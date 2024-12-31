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

    async def start(self):
        await super().start()
        if self.is_primary:
            if self.backup_address:
                await self._connect_to_backup()
            if self.second_layer_address:
                await self._connect_to_second_layer()
                self._sync_task = asyncio.create_task(self._time_sync_loop())

    async def ExecuteTransaction(self, request: replication_pb2.Transaction, context: grpc.aio.ServicerContext) -> replication_pb2.TransactionResponse:
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

            return replication_pb2.TransactionResponse(success=True, results=results)
        except Exception as e:
            self._logger.error(f"Read transaction failed: {e}")
            return replication_pb2.TransactionResponse(success=False, error_message=str(e))

    async def _connect_to_backup(self) -> None:
        try:
            channel = grpc.aio.insecure_channel(self.backup_address)
            self.backup_stub = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to backup at {self.backup_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to backup: {e}")

    async def _connect_to_second_layer(self) -> None:
        try:
            channel = grpc.aio.insecure_channel(self.second_layer_address)
            self.next_layer_stub = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to second layer at {self.second_layer_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to second layer: {e}")

    async def _time_sync_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._sync_interval)
                current_time = time.time()
                if current_time - self._last_sync_time >= self._sync_interval:
                    await self._notify_second_layer()
                    self._last_sync_time = current_time
            except Exception as e:
                self._logger.error(f"Time sync loop error: {e}")

    async def _notify_second_layer(self) -> None:
        try:
            updates = await self.store.get_recent_updates(10)
            notification = replication_pb2.LayerSyncNotification(
                updates=updates,
                source_node=self.node_id,
                layer=1
            )

            if self.next_layer_stub:
                await self.next_layer_stub.NotifyLayerSync(notification)
                self._logger.info(f"Notified second layer with {len(updates)} updates")
            else:
                self._logger.warning("No second layer connection available")

        except Exception as e:
            self._logger.error(f"Failed to notify second layer: {e}")