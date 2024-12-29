from typing import List, Dict
import asyncio
import grpc
from node.base_node import BaseNode
from proto import replication_pb2, replication_pb2_grpc

class CoreNode(BaseNode):
    """Core layer node implementation with update everywhere and eager replication.

    Args:
        node_id: Unique identifier for this node.
        log_dir: Directory for storing version logs.
        port: Port number for the gRPC server.
        peer_addresses: List of addresses for other core nodes.

    Attributes:
        peer_addresses: List of peer node addresses.
        peer_stubs: Dictionary mapping addresses to gRPC stubs.
        update_count: Counter for updates processed by this node.
    """

    def __init__(self, node_id: str, log_dir: str, port: int, peer_addresses: List[str]):
        super().__init__(node_id, layer=0, log_dir=log_dir, port=port)
        self.peer_addresses = peer_addresses
        self.peer_stubs: Dict[str, replication_pb2_grpc.NodeServiceStub] = {}
        self.update_count = 0
        self.server = None

    async def start(self):
        """Starts the node's gRPC server and connects to peer nodes."""
        self.server = grpc.aio.server()
        replication_pb2_grpc.add_NodeServiceServicer_to_server(self, self.server)
        listen_addr = f'[::]:{self.port}'
        self.server.add_insecure_port(listen_addr)
        await self.server.start()
        await self._connect_to_peers()
        return self

    async def stop(self):
        if self.server:
            await self.server.stop(grace=None)
            self.server = None
        for stub in self.peer_stubs.values():
            pass
        self.peer_stubs.clear()

    async def _connect_to_peers(self):
        """Establishes gRPC connections with all peer nodes."""
        for addr in self.peer_addresses:
            if addr != f'localhost:{self.port}':
                channel = grpc.aio.insecure_channel(addr)
                self.peer_stubs[addr] = replication_pb2_grpc.NodeServiceStub(channel)

    async def _propagate_to_peers(self, data_item: replication_pb2.DataItem) -> bool:
        """Propagates an update to all peer nodes.

        Args:
            data_item: The data item to propagate to peers.

        Returns:
            bool: True if all peers acknowledged the update successfully.
        """
        notification = replication_pb2.UpdateNotification(
            data=data_item,
            source_node=self.node_id
        )

        responses = await asyncio.gather(*[
            stub.PropagateUpdate(notification)
            for stub in self.peer_stubs.values()
        ], return_exceptions=True)

        return all(
            isinstance(r, replication_pb2.AckResponse) and r.success
            for r in responses
        )

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Executes a transaction and propagates updates to peers.

        Args:
            request: The transaction request containing operations.
            context: gRPC service context.

        Returns:
            TransactionResponse containing results or error information.
        """
        try:
            results = []
            for op in request.operations:
                if op.type == replication_pb2.Operation.READ:
                    item = self.store.get(op.key)
                    if item:
                        results.append(replication_pb2.DataItem(
                            key=item.key,
                            value=item.value,
                            version=item.version,
                            timestamp=int(item.timestamp)
                        ))
                elif op.type == replication_pb2.Operation.WRITE:
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

            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )
        except Exception as e:
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=str(e)
            )