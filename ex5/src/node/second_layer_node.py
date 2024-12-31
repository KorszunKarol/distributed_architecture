"""Second layer node implementation."""
import logging
import grpc
from typing import Optional
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
        backup_address: Optional[str] = None
    ):
        super().__init__(node_id, 2, log_dir, port, PassiveReplication())
        self.is_primary = is_primary
        self.backup_address = backup_address
        self.backup_stub = None
        self._logger = logging.getLogger(f"node.second_layer.{node_id}")

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
                    item = await self.store.get(op.key)
                    if item:
                        results.append(item)

            return replication_pb2.TransactionResponse(success=True, results=results)
        except Exception as e:
            self._logger.error(f"Read transaction failed: {e}")
            return replication_pb2.TransactionResponse(success=False, error_message=str(e))