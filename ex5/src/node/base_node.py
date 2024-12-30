"""Base node implementation for all layers."""
from typing import List, Optional
import asyncio
import grpc
from src.storage.data_store import DataStore
from src.proto import replication_pb2, replication_pb2_grpc
from src.replication.base_replication import BaseReplication

class BaseNode(replication_pb2_grpc.NodeServiceServicer):
    """Base node class with common functionality for all nodes.

    Provides basic functionality needed by all nodes:
    - Data storage
    - gRPC server setup
    - Basic status reporting
    """

    def __init__(self, node_id: str, layer: int, log_dir: str, port: int, replication_strategy: BaseReplication):
        """Initialize base node.

        Args:
            node_id: Unique identifier for this node
            layer: Layer number (0=core, 1=first, 2=second)
            log_dir: Directory for storing version logs
            port: Port number for gRPC server
            replication_strategy: Strategy for handling replication
        """
        self.node_id = node_id
        self.layer = layer
        self.port = port
        self.store = DataStore(node_id, log_dir)
        self.replication = replication_strategy
        self.replication.set_node(self)
        self.server = None
        self._closed = False

    async def start(self):
        """Start the node and replication strategy."""
        self.server = grpc.aio.server()
        replication_pb2_grpc.add_NodeServiceServicer_to_server(self, self.server)
        listen_addr = f'[::]:{self.port}'
        self.server.add_insecure_port(listen_addr)
        await self.server.start()
        await self.replication.start()
        return self

    async def stop(self):
        """Stop the node and cleanup."""
        self._closed = True
        await self.replication.stop()
        if self.server:
            await self.server.stop(grace=None)
            self.server = None

    async def GetNodeStatus(
        self,
        request: replication_pb2.Empty,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.NodeStatus:
        """Get current node status."""
        current_data = []
        for key, item in self.store.items():
            current_data.append(replication_pb2.DataItem(
                key=item.key,
                value=item.value,
                version=item.version,
                timestamp=int(item.timestamp)
            ))

        return replication_pb2.NodeStatus(
            node_id=self.node_id,
            layer=self.layer,
            current_data=current_data
        )