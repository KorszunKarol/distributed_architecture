import asyncio
import logging
from typing import Optional
import grpc
from src.node.base_node import BaseNode
from src.proto import replication_pb2, replication_pb2_grpc
from src.replication.passive_replication import PassiveReplication

class SecondLayerNode(BaseNode):
    """Second layer node implementing passive, primary-backup replication.

    C1 (primary):
    - Receives updates from B1 every 10 seconds
    - Propagates to C2 (backup)
    - Maintains oldest versions

    C2 (backup):
    - Only receives updates from C1
    - Maintains same versions as C1
    """

    def __init__(
        self,
        node_id: str,
        log_dir: str,
        port: int,
        is_primary: bool,
        backup_address: Optional[str] = None
    ):
        super().__init__(
            node_id=node_id,
            layer=2,
            log_dir=log_dir,
            port=port,
            replication_strategy=PassiveReplication()
        )
        self.is_primary = is_primary
        self.backup_address = backup_address
        self.backup_stub = None
        self._logger = logging.getLogger(f"node.second_layer.{node_id}")

    async def start(self) -> None:
        """Start the node and establish connections."""
        await super().start()
        self._logger.info(f"Starting second layer node {self.node_id}")
        if self.is_primary and self.backup_address:
            await self._connect_to_backup()

    async def _connect_to_backup(self) -> None:
        """Establish connection to backup node (C2)."""
        try:
            channel = grpc.aio.insecure_channel(self.backup_address)
            self.backup_stub = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to backup at {self.backup_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to backup: {e}")

    async def NotifyLayerSync(
        self,
        request: replication_pb2.LayerSyncNotification,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.AckResponse:
        """Handle updates from first layer (B1)."""
        if not self.is_primary:
            return replication_pb2.AckResponse(
                success=False,
                message="Updates must be sent to primary node"
            )

        try:
            # Apply updates locally and propagate to backup
            success = await self.replication_strategy.handle_update(request.updates)
            return replication_pb2.AckResponse(
                success=success,
                message="Updates processed successfully" if success else "Failed to process updates"
            )
        except Exception as e:
            self._logger.error(f"Failed to process layer sync: {e}")
            return replication_pb2.AckResponse(success=False, message=str(e))

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute read-only transactions."""
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