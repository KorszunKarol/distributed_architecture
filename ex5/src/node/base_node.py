"""Base node implementation for all layers."""
import asyncio
import grpc
from src.storage.data_store import DataStore
from src.proto import replication_pb2, replication_pb2_grpc
import logging

class BaseNode(replication_pb2_grpc.NodeServiceServicer):
    def __init__(self, node_id: str, layer: int, log_dir: str, port: int, replication_strategy):
        self.node_id = node_id
        self.layer = layer
        self.port = port
        self.store = DataStore(node_id, log_dir)
        self.replication = replication_strategy
        self.replication.set_node(self)
        self.server = None
        self._closed = False

    async def start(self):
        self.server = grpc.aio.server()
        replication_pb2_grpc.add_NodeServiceServicer_to_server(self, self.server)
        listen_addr = f'[::]:{self.port}'
        self.server.add_insecure_port(listen_addr)
        await self.server.start()
        await self.replication.start()
        return self

    async def stop(self):
        if hasattr(self, 'server'):
            await self.server.stop(5)
        if hasattr(self, 'store'):
            await self.store.close()
        if hasattr(self, 'replication'):
            await self.replication.stop()

    async def GetNodeStatus(self, request: replication_pb2.Empty, context: grpc.aio.ServicerContext) -> replication_pb2.NodeStatus:
        current_data = await self.store.get_all()
        return replication_pb2.NodeStatus(
            node_id=self.node_id,
            layer=self.layer,
            current_data=current_data
        )