from dataclasses import dataclass
from typing import List, Optional
from abc import ABC, abstractmethod
import asyncio
import grpc
from concurrent import futures

from src.storage.data_store import DataStore, DataItem
from src.proto import replication_pb2
from src.proto import replication_pb2_grpc
import pathlib


class BaseNode(replication_pb2_grpc.NodeServiceServicer):
    """Base node implementation providing common functionality for all layers.

    Args:
        node_id: Unique identifier for this node.
        layer: Layer number (0 for core, 1 for second, 2 for third).
        log_dir: Directory for storing version logs.
        port: Port number for the gRPC server.

    Attributes:
        node_id: Node's unique identifier.
        layer: Layer number in the architecture.
        store: Data store instance.
        port: Server port number.
    """

    def __init__(self, node_id: str, layer: int, log_dir: str, port: int):
        self.node_id = node_id
        self.layer = layer
        self.store = DataStore(node_id, pathlib.Path(log_dir))
        self.port = port
        self.server = None
        self.update_count = 0

    async def start(self):
        self._server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        replication_pb2_grpc.add_NodeServiceServicer_to_server(self, self._server)
        listen_addr = f'[::]:{self.port}'
        self._server.add_insecure_port(listen_addr)
        await self._server.start()

    async def stop(self):
        if hasattr(self, 'server') and self.server:
            try:
                await self.server.stop(grace=1)
                self.server = None
            except Exception as e:
                print(f"Error stopping server for {self.node_id}: {e}")

    async def PropagateUpdate(
        self,
        request: replication_pb2.UpdateNotification,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.AckResponse:
        try:
            item = request.data
            updated = await self.store.update(
                key=item.key,
                value=item.value,
                version=item.version
            )
            return replication_pb2.AckResponse(
                success=True,
                message=f"Update processed for key {item.key}"
            )
        except Exception as e:
            return replication_pb2.AckResponse(
                success=False,
                message=str(e)
            )

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute a transaction based on type and layer."""

        # Validate layer routing
        if request.type == replication_pb2.Transaction.READ_ONLY:
            if request.target_layer != self.layer:
                return replication_pb2.TransactionResponse(
                    success=False,
                    error_message=f"Transaction targeted for layer {request.target_layer}, but this is layer {self.layer}"
                )
        else:  # UPDATE transaction
            if self.layer != 0:
                return replication_pb2.TransactionResponse(
                    success=False,
                    error_message="Update transactions can only be executed on core layer"
                )

        results = []
        try:
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
                    if self.layer != 0:
                        raise ValueError("Write operations only allowed in core layer")

                    current_item = self.store.get(op.key)
                    new_version = (current_item.version + 1) if current_item else 1

                    item = await self.store.update(
                        key=op.key,
                        value=op.value,
                        version=new_version
                    )

                    results.append(replication_pb2.DataItem(
                        key=item.key,
                        value=item.value,
                        version=item.version,
                        timestamp=int(item.timestamp)
                    ))

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

    async def GetNodeStatus(self, request: replication_pb2.Empty, context=None) -> replication_pb2.NodeStatus:
        """Get current node status."""
        return replication_pb2.NodeStatus(
            node_id=self.node_id,
            layer=self.layer,
            update_count=self.update_count,
            current_data=[
                replication_pb2.DataItem(
                    key=item.key,
                    value=item.value,
                    version=item.version,
                    timestamp=int(item.timestamp)
                )
                for item in self.store.get_all_items()
            ]
        )