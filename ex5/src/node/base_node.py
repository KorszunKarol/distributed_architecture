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
    def __init__(self, node_id: str, layer: int, log_dir: str, port: int):
        self.node_id = node_id
        self.layer = layer
        self.store = DataStore(node_id, pathlib.Path(log_dir))
        self.port = port
        self._server = None

    async def start(self):
        self._server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        replication_pb2_grpc.add_NodeServiceServicer_to_server(self, self._server)
        listen_addr = f'[::]:{self.port}'
        self._server.add_insecure_port(listen_addr)
        await self._server.start()
        print(f"Node {self.node_id} listening on {listen_addr}")

    async def stop(self):
        if self._server:
            await self._server.stop(5)

    async def PropagateUpdate(
        self,
        request: replication_pb2.UpdateNotification,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.AckResponse:
        try:
            item = request.data
            updated = self.store.update(
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
                    item = self.store.update(
                        key=op.key,
                        value=op.value,
                        version=self.store.get(op.key).version + 1 if self.store.get(op.key) else 1
                    )
                    results.append(replication_pb2.DataItem(
                        key=item.key,
                        value=item.value,
                        version=item.version,
                        timestamp=int(item.timestamp)
                    ))

            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )
        except Exception as e:
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=str(e)
            )

    async def GetNodeStatus(
        self,
        request: replication_pb2.Empty,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.NodeStatus:
        items = self.store.get_all_items()
        return replication_pb2.NodeStatus(
            node_id=self.node_id,
            layer=self.layer,
            update_count=len(items),
            current_data=[
                replication_pb2.DataItem(
                    key=item.key,
                    value=item.value,
                    version=item.version,
                    timestamp=int(item.timestamp)
                ) for item in items
            ]
        )