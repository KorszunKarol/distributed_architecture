import asyncio
import logging
from typing import List, Dict, Optional
import grpc
from src.node.base_node import BaseNode
from src.proto import replication_pb2, replication_pb2_grpc
from src.replication.eager_replication import EagerReplication

class CoreNode(BaseNode):
    """Core layer node implementing eager, active, update-everywhere replication.

    This node belongs to layer 0 (core layer) and implements:
    - Update everywhere: Any node can accept updates
    - Active replication: All nodes process same operations
    - Eager replication: Waits for all acknowledgments before proceeding
    """

    def __init__(
        self,
        node_id: str,
        log_dir: str,
        port: int,
        peer_addresses: List[str],
        is_first_node: bool = False,
        first_layer_address: Optional[str] = None
    ):
        """Initialize core node.

        Args:
            node_id: Unique identifier for this node
            log_dir: Directory for storing version logs
            port: Port to listen on
            peer_addresses: Addresses of other core nodes
            is_first_node: Whether this is the designated first node (A1)
            first_layer_address: Address of B1 (only used if is_first_node)
        """
        super().__init__(
            node_id=node_id,
            layer=0,
            log_dir=log_dir,
            port=port,
            replication_strategy=EagerReplication()
        )
        self.peer_addresses = peer_addresses
        self.peer_stubs: Dict[str, replication_pb2_grpc.NodeServiceStub] = {}
        self.is_first_node = is_first_node
        self.first_layer_address = first_layer_address
        self.first_layer_stub = None
        self._update_counter = 0
        self._logger = logging.getLogger(f"node.core.{node_id}")

    async def start(self) -> None:
        """Start the node and establish connections."""
        await super().start()
        self._logger.info(f"Starting core node {self.node_id}")
        await self._connect_to_peers()
        if self.is_first_node and self.first_layer_address:
            await self._connect_to_first_layer()

    async def stop(self) -> None:
        """Stop the node and clean up connections."""
        self._logger.info(f"Stopping core node {self.node_id}")
        for channel in self.peer_stubs.values():
            await channel.channel.close()
        if self.first_layer_stub:
            await self.first_layer_stub.channel.close()
        await super().stop()

    async def _connect_to_peers(self) -> None:
        """Establish connections to peer core nodes."""
        for addr in self.peer_addresses:
            try:
                channel = grpc.aio.insecure_channel(addr)
                self.peer_stubs[addr] = replication_pb2_grpc.NodeServiceStub(channel)
                self._logger.info(f"Connected to peer at {addr}")
            except Exception as e:
                self._logger.error(f"Failed to connect to peer {addr}: {e}")

    async def _connect_to_first_layer(self) -> None:
        """Establish connection to first layer primary node (B1)."""
        try:
            channel = grpc.aio.insecure_channel(self.first_layer_address)
            self.first_layer_stub = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to first layer at {self.first_layer_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to first layer: {e}")

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute a transaction.

        For update transactions, uses eager replication to ensure all nodes
        receive and acknowledge updates before proceeding.
        """
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
        """Execute an update transaction with eager replication."""
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
                    # Handle eager replication
                    success = await self.replication_strategy.handle_update(data_item)
                    if not success:
                        raise Exception("Update replication failed")
                    results.append(data_item)

                    # Handle update counting and first layer notification
                    if self.is_first_node:
                        self._update_counter += 1
                        if self._update_counter >= 10:
                            await self._notify_first_layer()
                            self._update_counter = 0

                elif op.type == replication_pb2.Operation.READ:
                    item = await self.store.get(op.key)
                    if item:
                        results.append(item)

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
        """Execute a read-only transaction."""
        results = []
        try:
            for op in transaction.operations:
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

    async def _notify_first_layer(self) -> None:
        """Notify first layer after 10 updates."""
        try:
            updates = await self.store.get_recent_updates(10)
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