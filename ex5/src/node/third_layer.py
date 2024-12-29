from typing import List
import asyncio
import grpc
from src.node.base_node import BaseNode
from src.proto import replication_pb2, replication_pb2_grpc

class ThirdLayerNode(BaseNode):
    """Third layer node implementation with lazy replication every 10 seconds.

    Args:
        node_id: Unique identifier for this node.
        log_dir: Directory for storing version logs.
        port: Port number for the gRPC server.
        core_addresses: List of addresses for core layer nodes.
        primary_core: Address of the primary core node.

    Attributes:
        core_addresses: List of core node addresses.
        primary_core: Address of the primary core node.
        core_stubs: Dictionary mapping addresses to gRPC stubs.
    """

    def __init__(self, node_id: str, log_dir: str, port: int, core_addresses: List[str], primary_core: str):
        super().__init__(node_id, layer=2, log_dir=log_dir, port=port)
        self.core_addresses = core_addresses
        self.primary_core = primary_core
        self.core_stubs = {}
        self._sync_task = None

    async def start(self):
        await super().start()
        await self._connect_to_core()
        self._sync_task = asyncio.create_task(self._sync_loop())

    async def stop(self):
        if self.server:
            await self.server.stop(grace=None)
            self.server = None
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        await super().stop()

    async def _connect_to_core(self):
        for addr in self.core_addresses:
            channel = grpc.aio.insecure_channel(addr)
            self.core_stubs[addr] = replication_pb2_grpc.NodeServiceStub(channel)

    async def _sync_loop(self):
        while True:
            try:
                primary_stub = self.core_stubs[self.primary_core]
                status = await primary_stub.GetNodeStatus(replication_pb2.Empty())

                for item in status.current_data:
                    await self.store.update(
                        key=item.key,
                        value=item.value,
                        version=item.version
                    )
            except Exception as e:
                print(f"Sync error in {self.node_id}: {str(e)}")

            await asyncio.sleep(10)