"""Core node implementation."""
import asyncio
import logging
import grpc
from typing import Dict, List, Optional
from src.proto import replication_pb2, replication_pb2_grpc
from src.node.base_node import BaseNode
from src.replication.eager_replication import EagerReplication
import time

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
        self.replication.attach_node(self)
        self.peer_addresses = peer_addresses
        self.peer_stubs: Dict[str, replication_pb2_grpc.NodeServiceStub] = {}
        self.is_first_node = is_first_node
        self.first_layer_address = first_layer_address
        self.first_layer_stub = None
        self._update_counter = 0
        self._logger = logging.getLogger(f"node.core.{node_id}")
        self._logger.info(f"Initializing core node {node_id} with peers: {peer_addresses}")
        if is_first_node:
            self._logger.info(f"Node {node_id} is designated as first node with first layer at {first_layer_address}")

    async def start(self):
        self._logger.info(f"Starting core node {self.node_id}")
        await super().start()

        for addr in self.peer_addresses:
            self._logger.debug(f"Attempting to connect to peer at {addr}")
            await self._connect_to_peer(addr)

        if self.is_first_node and self.first_layer_address:
            max_retries = 5
            retry_delay = 1.0
            for i in range(max_retries):
                self._logger.debug(f"Attempting to connect to first layer at {self.first_layer_address} (attempt {i+1}/{max_retries})")
                await self._connect_to_first_layer()
                if self.first_layer_stub:
                    break
                if i < max_retries - 1:
                    self._logger.debug(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)

            if not self.first_layer_stub:
                self._logger.error("Failed to establish connection with first layer after all retries")

        self._logger.info(f"Core node {self.node_id} started successfully")

    async def _connect_to_peer(self, address: str) -> None:
        try:
            self._logger.debug(f"Creating channel to peer at {address}")
            channel = grpc.aio.insecure_channel(address)
            self.peer_stubs[address] = replication_pb2_grpc.NodeServiceStub(channel)
            self._logger.info(f"Connected to peer at {address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to peer {address}: {e}", exc_info=True)

    async def _connect_to_first_layer(self) -> None:
        try:
            self._logger.debug(f"Creating channel to first layer at {self.first_layer_address}")
            channel = grpc.aio.insecure_channel(self.first_layer_address)
            stub = replication_pb2_grpc.NodeServiceStub(channel)
            empty = replication_pb2.Empty()
            await stub.GetNodeStatus(empty)
            self.first_layer_stub = stub
            self._logger.info(f"Connected to first layer at {self.first_layer_address}")
        except Exception as e:
            self._logger.error(f"Failed to connect to first layer: {e}", exc_info=True)
            self.first_layer_stub = None

    async def _notify_first_layer(self) -> None:
        """Notify first layer of accumulated updates."""
        try:
            self._logger.debug("Preparing updates for first layer notification")
            updates = self.store.get_recent_updates(10)
            self._logger.debug(f"Got {len(updates)} recent updates to propagate")

            notification = replication_pb2.UpdateGroup(
                updates=updates,
                source_node=self.node_id,
                layer=0,
                update_count=self._update_counter
            )

            if self.first_layer_stub:
                self._logger.debug(f"Sending {len(updates)} updates to first layer")
                try:
                    response = await self.first_layer_stub.SyncUpdates(notification)
                    if response.success:
                        self._logger.info(f"Successfully notified first layer with {len(updates)} updates")
                    else:
                        self._logger.error(f"First layer rejected updates: {response.message}")
                except grpc.aio.AioRpcError as e:
                    self._logger.error(f"gRPC error while notifying first layer: {e.code()}: {e.details()}")
                    await self._connect_to_first_layer()
            else:
                self._logger.warning("No first layer connection available for notification")
                await self._connect_to_first_layer()

        except Exception as e:
            self._logger.error(f"Failed to notify first layer: {e}", exc_info=True)
            await self._connect_to_first_layer()

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        tx_type = "UPDATE" if request.type == replication_pb2.Transaction.UPDATE else "READ_ONLY"
        self._logger.info(f"Executing {tx_type} transaction with {len(request.operations)} operations")

        try:
            if request.type == replication_pb2.Transaction.UPDATE:
                return await self._execute_update_transaction(request)
            return await self._execute_read_transaction(request)
        except Exception as e:
            self._logger.error(f"Transaction failed: {e}", exc_info=True)
            raise

    async def _execute_update_transaction(
        self,
        request: replication_pb2.Transaction
    ) -> replication_pb2.TransactionResponse:
        """Execute an update transaction."""
        results = []
        try:
            for op in request.operations:
                if op.HasField('write'):
                    data_item = replication_pb2.DataItem(
                        key=op.write.key,
                        value=op.write.value,
                        version=self.store.get_next_version(),
                        timestamp=int(time.time())
                    )

                    await self.store.update(
                        key=data_item.key,
                        value=data_item.value,
                        version=data_item.version
                    )

                    update_request = replication_pb2.UpdateRequest(
                        update=data_item
                    )

                    await self.replication.handle_update(update_request)
                    results.append(data_item)

                    self._update_counter += 1
                    self._logger.debug(f"Update counter incremented to {self._update_counter}")

                    if self._update_counter >= 10 and self.is_first_node and self.first_layer_stub:
                        self._logger.info(f"Update threshold reached ({self._update_counter} updates), notifying first layer")
                        await self._notify_first_layer()
                        self._update_counter = 0
                        self._logger.debug("Update counter reset after first layer notification")

                elif op.HasField('read'):
                    item = await self.store.get(op.read.key)
                    if item:
                        results.append(item)

            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )
        except Exception as e:
            self._logger.error(f"Update transaction failed: {e}", exc_info=True)
            raise

    async def _execute_read_transaction(
        self,
        transaction: replication_pb2.Transaction
    ) -> replication_pb2.TransactionResponse:
        """Execute a read-only transaction."""
        self._logger.info(f"Processing read transaction with {len(transaction.operations)} operations for layer {transaction.target_layer}")

        if transaction.target_layer > 0:
            self._logger.info(f"Forwarding read transaction to layer {transaction.target_layer}")
            if transaction.target_layer == 1 and self.is_first_node and self.first_layer_stub:
                try:
                    self._logger.info("Forwarding read transaction to first layer")
                    response = await self.first_layer_stub.ExecuteTransaction(transaction)
                    if response.success:
                        self._logger.info(f"Successfully read from layer 1: {[r.value for r in response.results]}")
                    else:
                        self._logger.error(f"Failed to read from layer 1: {response.error_message}")
                        raise Exception(response.error_message)
                    return response
                except Exception as e:
                    error_msg = f"Failed to forward to layer 1: {str(e)}"
                    self._logger.error(error_msg)
                    raise
            else:
                error_msg = f"Cannot route to layer {transaction.target_layer}"
                self._logger.error(error_msg)
                raise Exception(error_msg)

        self._logger.info("Executing read transaction in core layer")
        results = []
        try:
            for i, op in enumerate(transaction.operations):
                if op.HasField('read'):
                    self._logger.info(f"Reading key {op.read.key} from core layer")
                    item = await self.store.get(op.read.key)
                    if item:
                        self._logger.info(f"Found value {item.value} for key {op.read.key} (version {item.version})")
                        results.append(item)
                    else:
                        self._logger.warning(f"No value found for key {op.read.key} in core layer")

            self._logger.info(f"Successfully completed read transaction with {len(results)} results from core layer")
            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )

        except Exception as e:
            error_msg = f"Read transaction failed in core layer: {e}"
            self._logger.error(error_msg, exc_info=True)
            raise

    async def PropagateUpdate(self, request: replication_pb2.UpdateNotification, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        """Handle update propagation from peer nodes."""
        self._logger.info(f"Received update propagation from {request.source_node} for key={request.data.key}")

        try:
            self._logger.debug("Delegating to replication strategy")
            await self.replication.PropagateUpdate(request, context)
            return replication_pb2.AckResponse(success=True)
        except Exception as e:
            error_msg = f"Failed to handle propagated update: {e}"
            self._logger.error(error_msg, exc_info=True)
            return replication_pb2.AckResponse(success=False, message=error_msg)