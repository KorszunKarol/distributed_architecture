from typing import List, Dict
import asyncio
import grpc
from node.base_node import BaseNode
from proto import replication_pb2, replication_pb2_grpc

class CoreNode(BaseNode):
    """Core layer node implementing eager, active, update-everywhere replication.
    This node belongs to layer 0 (core layer) and implements:
    - Update everywhere: Any node can accept updates
    - Active replication: All nodes process same operations in the same order
    - Eager replication: Waits for all acknowledgments before proceeding
    """

    def __init__(self, node_id: str, log_dir: str, port: int, peer_addresses: List[str]):
        """Initialize core node."""
        super().__init__(node_id, layer=0, log_dir=log_dir, port=port)
        self.peer_addresses = peer_addresses
        self.peer_stubs: Dict[str, replication_pb2_grpc.NodeServiceStub] = {}
        self.peer_channels: Dict[str, grpc.aio.Channel] = {}
        self.update_count = 0  # Only needed by core nodes
        self.sequence_number = 0  # For ordering transactions
        self.transaction_lock = asyncio.Lock()

    async def start(self):
        """Start the node and establish connections to peers."""
        print(f"Starting core node {self.node_id}")
        await super().start()
        print(f"Core node {self.node_id} server started")

        # Don't wait for peer connections during startup
        asyncio.create_task(self._connect_to_peers())
        print(f"Core node {self.node_id} connection task created")
        return self

    async def stop(self):
        """Stop the node and cleanup connections."""
        for addr, channel in self.peer_channels.items():
            try:
                await channel.close()
            except Exception as e:
                print(f"Error closing channel to {addr}: {e}")
        self.peer_channels.clear()
        self.peer_stubs.clear()

        await super().stop()

    async def _connect_to_peers(self):
        """Establish gRPC connections with all peer nodes."""
        while not hasattr(self, '_closed') or not self._closed:
            for addr in self.peer_addresses:
                if addr != f'localhost:{self.port}' and addr not in self.peer_stubs:
                    try:
                        channel = grpc.aio.insecure_channel(addr)
                        # Set a timeout for channel ready
                        try:
                            await asyncio.wait_for(channel.channel_ready(), timeout=2.0)
                            self.peer_channels[addr] = channel
                            self.peer_stubs[addr] = replication_pb2_grpc.NodeServiceStub(channel)
                            print(f"Node {self.node_id} successfully connected to peer {addr}")
                        except asyncio.TimeoutError:
                            print(f"Node {self.node_id} timeout connecting to {addr}, will retry")
                            continue
                    except Exception as e:
                        print(f"Node {self.node_id} failed to connect to peer {addr}: {e}")

            # If we have all peers connected, break
            if len(self.peer_stubs) == len(self.peer_addresses) - 1:
                print(f"Node {self.node_id} connected to all peers")
                break

            # Wait before retry
            await asyncio.sleep(1)

    async def _propagate_to_peers(self, data_item: replication_pb2.DataItem) -> bool:
        """Propagate an update to all peers eagerly.

        Args:
            data_item: The data item to propagate to peers

        Returns:
            bool: True if all peers acknowledged the update
        """
        notification = replication_pb2.UpdateNotification(
            data=data_item,
            source_node=self.node_id
        )

        try:
            responses = await asyncio.gather(*[
                stub.PropagateUpdate(
                    notification,
                    timeout=5.0
                )
                for stub in self.peer_stubs.values()
            ], return_exceptions=True)

            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    if isinstance(response, grpc.RpcError):
                        print(f"RPC failed for peer {list(self.peer_stubs.keys())[i]}: "
                              f"{response.code()}, {response.details()}")
                    else:
                        print(f"Error propagating to peer {list(self.peer_stubs.keys())[i]}: {response}")
                    return False
                elif not response.success:
                    print(f"Peer {list(self.peer_stubs.keys())[i]} rejected update: {response.message}")
                    return False

            return True

        except Exception as e:
            print(f"Unexpected error during propagation: {e}")
            return False

    async def PropagateUpdate(
        self,
        request: replication_pb2.UpdateNotification,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.AckResponse:
        """Handle update propagation from peers.

        Args:
            request: Update notification from peer
            context: gRPC context

        Returns:
            AckResponse indicating success/failure
        """
        try:
            await self.store.update(
                key=request.data.key,
                value=request.data.value,
                version=request.data.version
            )
            self.update_count += 1
            return replication_pb2.AckResponse(success=True)
        except Exception as e:
            error_msg = f"Failed to apply update: {str(e)}"
            print(error_msg)
            return replication_pb2.AckResponse(
                success=False,
                message=error_msg
            )

    async def GetNodeStatus(
        self,
        request: replication_pb2.Empty,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.NodeStatus:
        """Get current status of the node.

        Args:
            request: Empty request
            context: gRPC context

        Returns:
            NodeStatus containing current data and metadata
        """
        try:
            current_data = []
            for item in self.store.get_all():
                current_data.append(replication_pb2.DataItem(
                    key=item.key,
                    value=item.value,
                    version=item.version,
                    timestamp=int(item.timestamp)
                ))

            return replication_pb2.NodeStatus(
                node_id=self.node_id,
                current_data=current_data,
                update_count=self.update_count
            )
        except Exception as e:
            print(f"Error getting node status: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise


    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute a transaction with active replication.

        For update transactions:
        1. Acquire global order (using lock)
        2. Execute operations in order
        3. Propagate updates eagerly to all peers
        4. Wait for acknowledgments before proceeding

        Args:
            request: The transaction request
            context: gRPC context

        Returns:
            TransactionResponse with results or error
        """
        try:
            results = []

            if request.type == replication_pb2.Transaction.UPDATE:
                async with self.transaction_lock:
                    self.sequence_number += 1
                    current_seq = self.sequence_number

                    for op in request.operations:
                        if op.type == replication_pb2.Operation.WRITE:
                            try:
                                current_item = self.store.get(op.key)
                                new_version = (current_item.version + 1) if current_item else 1

                                item = await self.store.update(
                                    key=op.key,
                                    value=op.value,
                                    version=new_version
                                )

                                data_item = replication_pb2.DataItem(
                                    key=item.key,
                                    value=item.value,
                                    version=item.version,
                                    timestamp=int(item.timestamp)
                                )
                                results.append(data_item)

                                success = await self._propagate_to_peers(data_item)
                                if not success:
                                    raise Exception("Failed to propagate update to all peers")

                                self.update_count += 1
                            except Exception as e:
                                raise Exception(f"Failed to execute write operation: {e}")

            for op in request.operations:
                if op.type == replication_pb2.Operation.READ:
                    try:
                        item = self.store.get(op.key)
                        if item:
                            results.append(replication_pb2.DataItem(
                                key=item.key,
                                value=item.value,
                                version=item.version,
                                timestamp=int(item.timestamp)
                            ))
                    except Exception as e:
                        raise Exception(f"Failed to execute read operation: {e}")

            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )

        except Exception as e:
            error_msg = str(e)
            print(f"Transaction failed: {error_msg}")
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=error_msg
            )