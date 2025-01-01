"""First layer node implementation."""
import asyncio
import logging
import grpc
from typing import Optional
from src.proto import replication_pb2, replication_pb2_grpc
from src.node.base_node import BaseNode
import time
from src.replication.passive_replication import PassiveReplication

class FirstLayerNode(BaseNode):
    def __init__(
        self,
        node_id: str,
        log_dir: str,
        port: int,
        is_primary: bool,
        backup_address: Optional[str] = None,
        second_layer_address: Optional[str] = None
    ):
        super().__init__(node_id, 1, log_dir, port, PassiveReplication())
        self.is_primary = is_primary
        self.backup_address = backup_address
        self.second_layer_address = second_layer_address
        self.backup_stub = None
        self.next_layer_stub = None
        self._logger = logging.getLogger(f"node.first_layer.{node_id}")
        self._last_sync_time = time.time()
        self._sync_interval = 10.0
        self._sync_task = None
        self._pending_updates = []
        self._logger.info(f"Initializing first layer node {node_id} (primary={is_primary})")
        if backup_address:
            self._logger.info(f"Configured with backup at {backup_address}")
        if second_layer_address:
            self._logger.info(f"Configured with second layer at {second_layer_address}")

    async def start(self):
        self._logger.info(f"Starting first layer node {self.node_id}")
        await super().start()
        if self.is_primary:
            if self.backup_address:
                self._logger.debug(f"Connecting to backup at {self.backup_address}")
                await self._connect_to_backup()
            if self.second_layer_address:
                self._logger.debug(f"Connecting to second layer at {self.second_layer_address}")
                await self._connect_to_second_layer()
                self._sync_task = asyncio.create_task(self._time_sync_loop())
                self._logger.info("Started time sync loop")
        self._logger.info(f"First layer node {self.node_id} started successfully")

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
                if self.is_primary:
                    self._pending_updates.append(update)

            # Propagate to backup if we're primary
            if self.is_primary and self.backup_stub:
                self._logger.debug(f"Propagating {len(request.updates)} updates to backup")
                success = await self.replication.handle_update(request)
                if not success:
                    error_msg = "Replication failed"
                    self._logger.error(error_msg)
                    return replication_pb2.AckResponse(success=False, message=error_msg)

                self._logger.info(f"Successfully propagated {len(request.updates)} updates to backup")

                # Check if we should notify second layer
                if len(self._pending_updates) >= 10:
                    self._logger.info("Pending updates threshold reached, notifying second layer")
                    await self._notify_second_layer()
                    self._pending_updates = []

            return replication_pb2.AckResponse(success=True, message="")

        except Exception as e:
            self._logger.error(f"Failed to sync updates: {e}", exc_info=True)
            return replication_pb2.AckResponse(success=False, message=str(e))

    async def _connect_to_backup(self) -> None:
        try:
            self._logger.debug(f"Creating channel to backup at {self.backup_address}")
            channel = grpc.aio.insecure_channel(self.backup_address)
            self.backup_stub = replication_pb2_grpc.NodeServiceStub(channel)
            # Test the connection
            empty = replication_pb2.Empty()
            await self.backup_stub.GetNodeStatus(empty)
            self._logger.info(f"Connected to backup at {self.backup_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to backup: {e}", exc_info=True)
            self.backup_stub = None

    async def _connect_to_second_layer(self) -> None:
        try:
            self._logger.debug(f"Creating channel to second layer at {self.second_layer_address}")
            channel = grpc.aio.insecure_channel(self.second_layer_address)
            self.next_layer_stub = replication_pb2_grpc.NodeServiceStub(channel)
            # Test the connection
            empty = replication_pb2.Empty()
            await self.next_layer_stub.GetNodeStatus(empty)
            self._logger.info(f"Connected to second layer at {self.second_layer_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to second layer: {e}", exc_info=True)
            self.next_layer_stub = None

    async def _time_sync_loop(self) -> None:
        """Time-based sync loop for second layer propagation."""
        self._logger.info("Starting time sync loop")
        while True:
            try:
                await asyncio.sleep(self._sync_interval)
                current_time = time.time()
                
                # Always notify second layer every 10 seconds
                if current_time - self._last_sync_time >= self._sync_interval:
                    self._logger.info("Time sync interval reached (10s), notifying second layer")
                    await self._notify_second_layer()
                    self._last_sync_time = current_time
                    
            except Exception as e:
                self._logger.error(f"Time sync loop error: {e}", exc_info=True)

    async def _notify_second_layer(self) -> None:
        """Notify second layer of updates."""
        try:
            self._logger.info("Preparing updates for second layer notification (time-based)")
            # Get all updates for time-based sync
            updates = self.store.get_all()
            self._logger.info(f"Got {len(updates)} updates to propagate to second layer")

            if not updates:
                self._logger.debug("No updates to propagate")
                return

            notification = replication_pb2.LayerSyncNotification(
                updates=updates,
                source_node=self.node_id,
                source_layer=self.layer,
                target_layer=2,
                update_count=len(updates),
                sync_timestamp=int(time.time())
            )

            if self.next_layer_stub:
                self._logger.info(f"Sending {len(updates)} updates to second layer")
                try:
                    response = await self.next_layer_stub.NotifyLayerSync(notification)
                    if response.success:
                        self._logger.info(f"Successfully sent {len(updates)} updates to second layer")
                    else:
                        self._logger.error(f"Second layer rejected updates: {response.message}")
                except grpc.aio.AioRpcError as e:
                    self._logger.error(f"gRPC error while notifying second layer: {e.code()}: {e.details()}")
                    await self._connect_to_second_layer()
            else:
                self._logger.warning("No second layer connection available for notification")
                await self._connect_to_second_layer()

        except Exception as e:
            self._logger.error(f"Failed to notify second layer: {e}", exc_info=True)
            await self._connect_to_second_layer()