"""Second layer node implementation."""
import logging
import grpc
from typing import Optional, List, Dict
from src.proto import replication_pb2, replication_pb2_grpc
from src.node.base_node import BaseNode
from src.replication.passive_replication import PassiveReplication
import asyncio

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

    async def start(self):
        await super().start()
        if self.is_primary:
            for addr in self.backup_addresses:
                await self._connect_to_backup(addr)

    async def _connect_to_backup(self, address: str) -> None:
        try:
            channel = grpc.aio.insecure_channel(address)
            self.backup_stubs[address] = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to backup at {address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to backup {address}: {e}")

    async def ExecuteTransaction(self, request: replication_pb2.Transaction, context: grpc.aio.ServicerContext) -> replication_pb2.TransactionResponse:
        if request.type != replication_pb2.Transaction.READ_ONLY:
            return replication_pb2.TransactionResponse(
                success=False,
                error_message="Second layer only accepts read-only transactions"
            )

        results = []
        try:
            for op in request.operations:
                if op.type == replication_pb2.Operation.READ:
                    item = self.store.get(op.key)
                    if item:
                        results.append(item)

            return replication_pb2.TransactionResponse(success=True, results=results)
        
        
        except Exception as e:
            self._logger.error(f"Read transaction failed: {e}")
            return replication_pb2.TransactionResponse(success=False, error_message=str(e))

    async def NotifyLayerSync(self, request: replication_pb2.LayerSyncNotification, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        try:
            for update in request.updates:
                await self.store.update(
                    key=update.key,
                    value=update.value,
                    version=update.version
                )

            if self.is_primary and self.backup_stubs:
                backup_request = replication_pb2.LayerSyncNotification(
                    updates=request.updates,
                    source_node=self.node_id,
                    layer=self.layer,
                    source_layer=request.source_layer,
                    target_layer=request.target_layer
                )
                await asyncio.gather(*[
                    stub.NotifyLayerSync(backup_request)
                    for stub in self.backup_stubs.values()
                ])

            return replication_pb2.AckResponse(success=True)

        except Exception as e:
            self._logger.error(f"Failed to sync layer updates: {e}")
            return replication_pb2.AckResponse(success=False, message=str(e))