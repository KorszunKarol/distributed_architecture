"""Core node implementation."""
import asyncio
import logging
import grpc
from typing import List, Dict, Optional
from src.proto import replication_pb2, replication_pb2_grpc
from src.node.base_node import BaseNode
from src.replication.eager_replication import EagerReplication

class CoreNode(BaseNode):
    def __init__(
        self,
        node_id: str,
        log_dir: str,
        port: int,
        peer_addresses: List[str],
        is_first_node: bool = False,
        first_layer_address: Optional[str] = None
    ):
        super().__init__(node_id, 0, log_dir, port, EagerReplication())
        self.peer_addresses = peer_addresses
        self.peer_stubs: Dict[str, replication_pb2_grpc.NodeServiceStub] = {}
        self.is_first_node = is_first_node
        self.first_layer_address = first_layer_address
        self.first_layer_stub = None
        self._update_counter = 0
        self._logger = logging.getLogger(f"node.core.{node_id}")

    async def start(self):
        await super().start()
        for addr in self.peer_addresses:
            await self._connect_to_peer(addr)
        if self.is_first_node and self.first_layer_address:
            await self._connect_to_first_layer()

    async def _connect_to_peer(self, address: str) -> None:
        try:
            channel = grpc.aio.insecure_channel(address)
            self.peer_stubs[address] = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to peer at {address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to peer {address}: {e}")

    async def _connect_to_first_layer(self) -> None:
        try:
            channel = grpc.aio.insecure_channel(self.first_layer_address)
            self.first_layer_stub = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to first layer at {self.first_layer_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to first layer: {e}")

    async def _notify_first_layer(self) -> None:
        try:
            updates = self.store.get_recent_updates(10)
            notification = replication_pb2.UpdateGroup(
                updates=updates,
                source_node=self.node_id,
                layer=0,
                update_count=self._update_counter
            )

            if self.first_layer_stub:
                await self.first_layer_stub.SyncUpdates(notification)
                self._logger.info(f"Notified first layer with {len(updates)} updates")
            else:
                self._logger.warning("No first layer connection available")

        except Exception as e:
            self._logger.error(f"Failed to notify first layer: {e}")

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        try:
            if request.type == replication_pb2.Transaction.UPDATE:
                return await self._execute_update_transaction(request)
            return await self._execute_read_transaction(request)
        except Exception as e:
            self._logger.error(f"Transaction failed: {e}")
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=str(e)
            )

    async def _execute_update_transaction(
        self,
        transaction: replication_pb2.Transaction
    ) -> replication_pb2.TransactionResponse:
        results = []
        try:
            for op in transaction.operations:
                if op.type == replication_pb2.Operation.WRITE:
                    data_item = replication_pb2.DataItem(
                        key=op.key,
                        value=op.value,
                        version=self.store.get_next_version(),
                        timestamp=int(asyncio.get_event_loop().time())
                    )
                    success = await self.replication.handle_update(data_item)
                    if not success:
                        raise Exception("Update replication failed")
                    results.append(data_item)

            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )

        except Exception as e:
            self._logger.error(f"Update transaction failed: {e}")
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=str(e)
            )

    async def _execute_read_transaction(
        self,
        transaction: replication_pb2.Transaction
    ) -> replication_pb2.TransactionResponse:
        results = []
        try:
            for op in transaction.operations:
                if op.type == replication_pb2.Operation.READ:
                    item = self.store.get(op.key)
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

    async def PropagateUpdate(self, request: replication_pb2.UpdateNotification, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        """Handle update propagation from peer nodes."""
        try:
            # Delegate to replication strategy
            response = await self.replication.PropagateUpdate(request)
            
            # Only handle counter in PropagateUpdate
            if response.success and self.is_first_node:
                self._update_counter += 1
                if self._update_counter >= 10:
                    await self._notify_first_layer()
                    self._update_counter = 0
            
            return response

        except Exception as e:
            self._logger.error(f"Failed to propagate update: {e}")
            return replication_pb2.AckResponse(
                success=False,
                message=str(e)
            )