import asyncio
import logging
from typing import Optional
import grpc
from src.node.base_node import BaseNode
from src.proto import replication_pb2, replication_pb2_grpc
from src.replication.passive_replication import PassiveReplication
import time

class FirstLayerNode(BaseNode):
    """First layer node implementing passive, primary-backup replication.

    B1 (primary):
    - Receives updates from core layer (A1) every 10 updates
    - Propagates to B2 (backup)
    - Notifies second layer (C1) every 10 seconds

    B2 (backup):
    - Only receives updates from B1
    """

    def __init__(
        self,
        node_id: str,
        log_dir: str,
        port: int,
        is_primary: bool,
        backup_address: Optional[str] = None,
        second_layer_address: Optional[str] = None
    ):
        super().__init__(
            node_id=node_id,
            layer=1,
            log_dir=log_dir,
            port=port,
            replication_strategy=PassiveReplication()
        )
        self.is_primary = is_primary
        self.backup_address = backup_address
        self.second_layer_address = second_layer_address
        self.backup_stub = None
        self.next_layer_stub = None
        self._logger = logging.getLogger(f"node.first_layer.{node_id}")
        self._last_sync_time = time.time()
        self._sync_interval = 10.0
        self._sync_task = None

    async def start(self) -> None:
        """Start the node and establish connections."""
        await super().start()
        self._logger.info(f"Starting first layer node {self.node_id}")

        if self.is_primary:
            if self.backup_address:
                await self._connect_to_backup()
            if self.second_layer_address:
                await self._connect_to_second_layer()
                self._sync_task = asyncio.create_task(self._time_sync_loop())

    async def stop(self) -> None:
        """Stop the node and clean up connections."""
        self._logger.info(f"Stopping first layer node {self.node_id}")
        if self.backup_stub:
            await self.backup_stub.channel.close()
        if self.next_layer_stub:
            await self.next_layer_stub.channel.close()
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        await super().stop()

    async def _connect_to_backup(self) -> None:
        """Establish connection to backup node (B2)."""
        try:
            channel = grpc.aio.insecure_channel(self.backup_address)
            self.backup_stub = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to backup at {self.backup_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to backup: {e}")

    async def _connect_to_second_layer(self) -> None:
        """Establish connection to second layer primary (C1)."""
        try:
            channel = grpc.aio.insecure_channel(self.second_layer_address)
            self.next_layer_stub = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to second layer at {self.second_layer_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to second layer: {e}")

    async def _time_sync_loop(self) -> None:
        """Send updates to second layer every 10 seconds."""
        while True:
            try:
                await asyncio.sleep(1)
                current_time = time.time()
                if current_time - self._last_sync_time >= self._sync_interval:
                    await self._notify_second_layer()
                    self._last_sync_time = current_time
            except Exception as e:
                self._logger.error(f"Error in time sync loop: {e}")

    async def _notify_second_layer(self) -> None:
        """Send current state to second layer."""
        if not self.next_layer_stub:
            return

        try:
            updates = await self.store.get_all()
            notification = replication_pb2.LayerSyncNotification(
                source_layer=self.layer,
                target_layer=self.layer + 1,
                updates=updates,
                sync_timestamp=int(time.time())
            )
            await self.next_layer_stub.NotifyLayerSync(notification)
            self._logger.info(f"Sent {len(updates)} updates to second layer")
        except Exception as e:
            self._logger.error(f"Failed to notify second layer: {e}")

    async def SyncUpdates(
        self,
        request: replication_pb2.UpdateGroup,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.AckResponse:
        """Handle updates from core layer (if primary) or from primary (if backup)."""
        try:
            success = await self.replication_strategy.handle_update(request.updates)
            return replication_pb2.AckResponse(
                success=success,
                message="Updates processed successfully" if success else "Failed to process updates"
            )
        except Exception as e:
            self._logger.error(f"Failed to process updates: {e}")
            return replication_pb2.AckResponse(success=False, message=str(e))

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute read-only transactions (writes only go to core layer)."""
        if request.type != replication_pb2.Transaction.READ_ONLY:
            return replication_pb2.TransactionResponse(
                success=False,
                error_message="First layer only accepts read-only transactions"
            )

        results = []
        try:
            for op in request.operations:
                if op.type == replication_pb2.Operation.READ:
                    item = await self.store.get(op.key)
                    if item:
                        results.append(item)

            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )

        except Exception as e:
            self._logger.error(f"Read transaction failed: {e}")
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=str(e)
            )