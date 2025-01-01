"""Second layer node implementation."""
import asyncio
import logging
import grpc
from typing import Dict, List
from src.proto import replication_pb2, replication_pb2_grpc
from src.node.base_node import BaseNode
from src.replication.passive_replication import PassiveReplication

class SecondLayerNode(BaseNode):
    def __init__(
        self,
        node_id: str,
        log_dir: str,
        port: int,
        is_primary: bool,
        backup_addresses: List[str] = None
    ):
        super().__init__(node_id, 2, log_dir, port, PassiveReplication())
        self.is_primary = is_primary
        self.backup_addresses = backup_addresses or []
        self.backup_stubs: Dict[str, replication_pb2_grpc.NodeServiceStub] = {}
        self._logger = logging.getLogger(f"node.second_layer.{node_id}")
        self._logger.info(f"Initializing second layer node {node_id} (primary={is_primary})")
        if backup_addresses:
            self._logger.info(f"Configured with backups: {backup_addresses}")

    async def start(self):
        self._logger.info(f"Starting second layer node {self.node_id}")
        await super().start()
        if self.is_primary:
            for addr in self.backup_addresses:
                self._logger.debug(f"Connecting to backup at {addr}")
                await self._connect_to_backup(addr)
        self._logger.info(f"Second layer node {self.node_id} started successfully")

    async def _connect_to_backup(self, address: str) -> None:
        try:
            self._logger.debug(f"Creating channel to backup at {address}")
            channel = grpc.aio.insecure_channel(address)
            stub = replication_pb2_grpc.NodeServiceStub(channel)
            # Test the connection
            empty = replication_pb2.Empty()
            await stub.GetNodeStatus(empty)
            self.backup_stubs[address] = stub
            self._logger.info(f"Connected to backup at {address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to backup {address}: {e}", exc_info=True)

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        tx_type = "READ_ONLY" if request.type == replication_pb2.Transaction.READ_ONLY else "UPDATE"
        self._logger.info(f"Received {tx_type} transaction with {len(request.operations)} operations")

        # Reject write operations
        if request.type == replication_pb2.Transaction.UPDATE:
            error_msg = "Write operations not allowed"
            self._logger.warning(f"Rejected {tx_type} transaction: {error_msg}")
            raise Exception(error_msg)

        # Also check for write operations in the transaction
        for op in request.operations:
            if op.type == replication_pb2.Operation.WRITE:
                error_msg = "Write operations not allowed"
                self._logger.warning(f"Rejected transaction with write operation: {error_msg}")
                raise Exception(error_msg)

        results = []
        try:
            for i, op in enumerate(request.operations):
                if op.type == replication_pb2.Operation.READ:
                    self._logger.debug(f"Processing read operation {i+1}/{len(request.operations)}: key={op.key}")
                    item = await self.store.get(op.key)
                    if item:
                        self._logger.debug(f"Found value for key={op.key}: version={item.version}")
                        results.append(item)
                    else:
                        self._logger.debug(f"No value found for key={op.key}")

            self._logger.info(f"Successfully completed read transaction with {len(results)} results")
            return replication_pb2.TransactionResponse(success=True, results=results)
        
        except Exception as e:
            self._logger.error(f"Read transaction failed: {e}", exc_info=True)
            raise  # Re-raise the exception instead of returning error response

    async def SyncUpdates(self, request: replication_pb2.UpdateGroup, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        self._logger.info(f"Received sync request from {request.source_node} with {len(request.updates)} updates")
        try:
            # Store updates locally
            for i, update in enumerate(request.updates):
                self._logger.debug(f"Processing update {i+1}/{len(request.updates)}: key={update.key}, version={update.version}")
                await self.store.update(
                    key=update.key,
                    value=update.value,
                    version=update.version
                )
                self._logger.debug(f"Stored update for key={update.key}")

            # Propagate to backups if we're primary
            if self.is_primary and self.backup_stubs:
                self._logger.debug(f"Propagating {len(request.updates)} updates to {len(self.backup_stubs)} backups")
                success = await self.replication.handle_update(request)
                if not success:
                    error_msg = "Replication failed"
                    self._logger.error(error_msg)
                    return replication_pb2.AckResponse(success=False, message=error_msg)

                self._logger.info(f"Successfully propagated {len(request.updates)} updates to backups")

            return replication_pb2.AckResponse(success=True, message="")

        except Exception as e:
            self._logger.error(f"Failed to sync updates: {e}", exc_info=True)
            return replication_pb2.AckResponse(success=False, message=str(e))

    async def NotifyLayerSync(self, request: replication_pb2.LayerSyncNotification, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        self._logger.info(f"Received layer sync from {request.source_node} with {len(request.updates)} updates")
        try:
            for i, update in enumerate(request.updates):
                self._logger.debug(f"Processing update {i+1}/{len(request.updates)}: key={update.key}, version={update.version}")
                await self.store.update(
                    key=update.key,
                    value=update.value,
                    version=update.version
                )
                self._logger.debug(f"Stored update for key={update.key}")

            if self.is_primary and self.backup_stubs:
                self._logger.debug(f"Propagating {len(request.updates)} updates to {len(self.backup_stubs)} backups")
                backup_request = replication_pb2.LayerSyncNotification(
                    updates=request.updates,
                    source_node=self.node_id,
                    source_layer=self.layer,
                    target_layer=request.target_layer,
                    update_count=len(request.updates),
                    sync_timestamp=int(asyncio.get_event_loop().time())
                )
                
                propagation_tasks = [
                    stub.NotifyLayerSync(backup_request)
                    for stub in self.backup_stubs.values()
                ]
                
                try:
                    responses = await asyncio.gather(*propagation_tasks, return_exceptions=True)
                    for i, response in enumerate(responses):
                        if isinstance(response, Exception):
                            self._logger.error(f"Backup {i} failed with error: {response}")
                        elif not response.success:
                            self._logger.error(f"Backup {i} rejected update: {response.error}")
                except Exception as e:
                    self._logger.error(f"Failed to propagate to backups: {e}", exc_info=True)

            self._logger.info(f"Successfully processed layer sync with {len(request.updates)} updates")
            return replication_pb2.AckResponse(success=True, message="")

        except Exception as e:
            self._logger.error(f"Failed to sync layer updates: {e}", exc_info=True)
            return replication_pb2.AckResponse(success=False, message=str(e))