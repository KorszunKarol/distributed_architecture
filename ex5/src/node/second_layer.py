from typing import List
import asyncio
import grpc
from src.node.base_node import BaseNode
from src.proto import replication_pb2, replication_pb2_grpc

class SecondLayerNode(BaseNode):
    """Second layer node implementation with lazy replication every 10 updates.

    Args:
        node_id: Unique identifier for this node.
        log_dir: Directory for storing version logs.
        port: Port number for the gRPC server.
        core_addresses: List of addresses for core layer nodes.
        primary_core: Address of the primary core node.

    Attributes:
        core_addresses: List of core node addresses.
        primary_core: Address of the primary core node.
        primary_stub: gRPC stub for the primary core node.
        update_count: Last known update count from primary.
        last_sync_count: Last known update count from primary.
    """

    def __init__(self, node_id: str, log_dir: str, port: int, core_addresses: List[str], primary_core: str):
        super().__init__(node_id, layer=1, log_dir=log_dir, port=port)
        self.core_addresses = core_addresses
        self.primary_core = primary_core
        self.primary_stub = None
        self.update_count = 0
        self.last_sync_count = 0

    async def start(self):
        self.server = grpc.aio.server()
        replication_pb2_grpc.add_NodeServiceServicer_to_server(self, self.server)
        listen_addr = f'[::]:{self.port}'
        self.server.add_insecure_port(listen_addr)
        await self.server.start()

        channel = grpc.aio.insecure_channel(self.primary_core)
        self.primary_stub = replication_pb2_grpc.NodeServiceStub(channel)

        asyncio.create_task(self._sync_loop())
        return self

    async def _sync_loop(self):
        while True:
            try:
                status = await self.primary_stub.GetNodeStatus(replication_pb2.Empty())
                if status.update_count >= self.last_sync_count + 10:
                    for item in status.current_data:
                        await self.store.update(
                            key=item.key,
                            value=item.value,
                            version=item.version
                        )
                    self.last_sync_count = status.update_count
                    self.update_count = status.update_count
            except Exception as e:
                print(f"Sync error in {self.node_id}: {e}")
            await asyncio.sleep(1)

    async def stop(self):
        if self.server:
            await self.server.stop(grace=None)
            self.server = None