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
        self.backup_stubs = {}  # Dictionary to store stubs by address
        self._logger = logging.getLogger(f"node.second_layer.{node_id}")
        self._logger.info(f"Initializing second layer node {node_id} (primary={is_primary})")
        if backup_addresses:
            self._logger.info(f"Configured with backups: {backup_addresses}")

    async def start(self):
        """Start the second layer node."""
        self._logger.info(f"Starting second layer node {self.node_id}")
        await super().start()

        # Connect to backup/primary nodes
        for addr in self.backup_addresses:
            await self._connect_to_backup(addr)

        # Update replication strategy with connected stubs
        if hasattr(self.replication, 'set_backup_stubs'):
            self.replication.set_backup_stubs(list(self.backup_stubs.values()))

        self._logger.info(f"Second layer node {self.node_id} started successfully")

    async def _connect_to_backup(self, address: str) -> None:
        """Connect to a backup node with retries."""
        max_retries = 5
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                self._logger.debug(f"Creating channel to node at {address}")
                channel = grpc.aio.insecure_channel(address)
                stub = replication_pb2_grpc.NodeServiceStub(channel)

                # Verify connection by getting node status
                empty = replication_pb2.Empty()
                await stub.GetNodeStatus(empty)

                self._logger.info(f"Connected to node at {address}")
                self.backup_stubs[address] = stub
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    self._logger.debug(f"Attempt {attempt + 1} failed to connect to {address}: {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    self._logger.warning(f"Failed to connect to backup at {address} after {max_retries} attempts")

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        tx_type = "READ_ONLY" if request.type == replication_pb2.Transaction.READ_ONLY else "UPDATE"
        self._logger.info(f"Received {tx_type} transaction with {len(request.operations)} operations")

        if request.type == replication_pb2.Transaction.UPDATE:
            error_msg = "Write operations not allowed"
            self._logger.warning(f"Rejected {tx_type} transaction: {error_msg}")
            raise Exception(error_msg)

        for op in request.operations:
            if op.HasField('write'):
                error_msg = "Write operations not allowed"
                self._logger.warning(f"Rejected transaction with write operation: {error_msg}")
                raise Exception(error_msg)

        results = []
        try:
            for i, op in enumerate(request.operations):
                if op.HasField('read'):
                    self._logger.debug(f"Processing read operation {i+1}/{len(request.operations)}: key={op.read.key}")
                    item = await self.store.get(op.read.key)
                    if item:
                        self._logger.debug(f"Found value for key={op.read.key}: version={item.version}")
                        results.append(item)
                    else:
                        self._logger.debug(f"No value found for key={op.read.key}")

            self._logger.info(f"Successfully completed read transaction with {len(results)} results")
            return replication_pb2.TransactionResponse(success=True, results=results)

        except Exception as e:
            self._logger.error(f"Read transaction failed: {e}", exc_info=True)
            raise

    async def SyncUpdates(self, request: replication_pb2.UpdateGroup, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        self._logger.info(f"Received sync request from {request.source_node} with {len(request.updates)} updates")
        try:
            # Don't reset counter, just process new updates
            for update in request.updates:
                # Only increment if we haven't seen this version before
                current = await self.store.get(update.key)
                if not current or current.version < update.version:
                    await self.store.update(
                        key=update.key,
                        value=update.value,
                        version=update.version
                    )
                    self.websocket_client.increment_update_count()
                    self.websocket_client.update_sync_time()

            if self.is_primary and self.backup_stubs:
                success = await self.replication.handle_update(request)
                if not success:
                    return replication_pb2.AckResponse(success=False, message="Replication failed")

            return replication_pb2.AckResponse(success=True)

        except Exception as e:
            return replication_pb2.AckResponse(success=False, message=str(e))

    async def PropagateUpdate(
        self,
        request: replication_pb2.UpdateNotification,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.AckResponse:
        """Handle update propagation from primary node."""
        try:
            # Store the update locally
            data = request.data
            await self.store.update(
                key=data.key,
                value=data.value,
                version=data.version
            )

            # Update monitoring stats
            self.websocket_client.increment_update_count()
            self.websocket_client.update_sync_time()

            self._logger.info(f"Successfully processed update for key={data.key}")
            return replication_pb2.AckResponse(success=True)

        except Exception as e:
            error_msg = f"Failed to handle propagated update: {e}"
            self._logger.error(error_msg, exc_info=True)
            return replication_pb2.AckResponse(success=False, message=error_msg)
