"""Base node implementation for all layers."""
import asyncio
import grpc
from src.storage.data_store import DataStore
from src.proto import replication_pb2, replication_pb2_grpc
from src.monitor.websocket_client import NodeWebSocketClient
import logging
import time
from typing import Dict, Any

class BaseNode(replication_pb2_grpc.NodeServiceServicer):
    """Base node implementation for all layers.

    Attributes:
        node_id: Unique identifier for the node
        layer: Layer number (0=core, 1=first, 2=second)
        port: Port number for gRPC server
        store: Data store instance
        replication: Replication strategy
        server: gRPC server instance
        websocket_client: WebSocket client for monitoring
    """

    def __init__(self, node_id: str, layer: int, log_dir: str, port: int, replication_strategy):
        """Initialize base node.

        Args:
            node_id: Unique identifier for the node
            layer: Layer number (0=core, 1=first, 2=second)
            log_dir: Directory for storing logs
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
        self._ready = asyncio.Event()
        self._logger = logging.getLogger(f"node.base.{node_id}")
        self._logger.info(f"Initializing base node {node_id} at layer {layer} on port {port}")
        self.websocket_client = NodeWebSocketClient(node_id, layer)
        self.websocket_client._get_current_data = self._get_websocket_data
        self.websocket_client._get_operation_log = self._get_websocket_operation_log

    async def _get_websocket_data(self) -> Dict[str, Any]:
        """Get current data for WebSocket monitoring."""
        try:
            data = await self.store.get_all()
            return {str(item.key): str(item.value) for item in data}
        except Exception as e:
            self._logger.error(f"Error getting WebSocket data: {e}")
            return {}

    async def _get_websocket_operation_log(self) -> list:
        """Get operation log for WebSocket monitoring."""
        try:
            return await self.store.get_operation_log()
        except Exception as e:
            self._logger.error(f"Error getting operation log: {e}")
            return []

    async def start(self):
        """Start the node's gRPC server and replication strategy."""
        self._logger.info(f"Starting base node {self.node_id}")
        try:
            self.server = grpc.aio.server()
            replication_pb2_grpc.add_NodeServiceServicer_to_server(self, self.server)
            listen_addr = f'[::]:{self.port}'
            self._logger.debug(f"Adding insecure port {listen_addr}")
            self.server.add_insecure_port(listen_addr)
            self._logger.debug("Starting gRPC server")
            await self.server.start()
            self._logger.debug("Starting replication strategy")
            await self.replication.start()
            self._logger.debug("Starting WebSocket client")
            await self.websocket_client.start()
            self._ready.set()
            self._logger.info(f"Base node {self.node_id} started successfully")
            return self
        except Exception as e:
            self._logger.error(f"Failed to start node: {e}")
            raise

    async def wait_for_ready(self, timeout: float = 5.0):
        """Wait for the node to be ready.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            bool: True if node is ready, False if timeout occurred
        """
        try:
            await asyncio.wait_for(self._ready.wait(), timeout)
            self._logger.debug(f"Node {self.node_id} is ready")
            return True
        except asyncio.TimeoutError:
            self._logger.error(f"Timeout waiting for node {self.node_id} to be ready")
            return False

    async def stop(self):
        """Stop the node's gRPC server and cleanup resources."""
        self._logger.info(f"Stopping base node {self.node_id}")
        try:
            if hasattr(self, 'websocket_client'):
                self._logger.debug("Stopping WebSocket client")
                await self.websocket_client.stop()
            if hasattr(self, 'server') and self.server is not None:
                self._logger.debug("Stopping gRPC server")
                await self.server.stop(5)
            if hasattr(self, 'store'):
                self._logger.debug("Closing data store")
                await self.store.close()
            if hasattr(self, 'replication'):
                self._logger.debug("Stopping replication strategy")
                await self.replication.stop()
            self._ready.clear()
            self._closed = True
            self._logger.info(f"Base node {self.node_id} stopped successfully")
        except Exception as e:
            self._logger.error(f"Error during node shutdown: {e}")
            raise

    async def GetNodeStatus(self, request: replication_pb2.Empty, context: grpc.aio.ServicerContext) -> replication_pb2.NodeStatus:
        """Get the current status of the node.

        Args:
            request: Empty request
            context: gRPC service context

        Returns:
            NodeStatus containing current node information

        Raises:
            Exception: If there's an error getting node status
        """
        self._logger.debug("Getting node status")
        try:
            current_data = await self.store.get_all()
            self._logger.debug(f"Retrieved {len(current_data)} data items")
            status = replication_pb2.NodeStatus(
                node_id=self.node_id,
                layer=self.layer,
                current_data=current_data
            )
            return status
        except Exception as e:
            self._logger.error(f"Failed to get node status: {e}", exc_info=True)
            raise

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute a transaction on this node."""
        tx_type = "READ_ONLY" if request.type == replication_pb2.Transaction.READ_ONLY else "UPDATE"

        transaction = {
            'timestamp': time.time(),
            'command': str(request),
            'node_id': self.node_id,
            'status': 'pending',
            'target_layer': self.layer,
            'error': None
        }

        try:
            response = await self._execute_update_transaction(request)

            transaction['status'] = 'success'

            # Update WebSocket metrics
            if tx_type == "UPDATE":
                self.websocket_client.increment_update_count()
            self.websocket_client.update_sync_time()

            if hasattr(self, 'monitor'):
                await self.monitor.add_transaction(transaction)

            return response

        except Exception as e:
            transaction['status'] = 'failed'
            transaction['error'] = str(e)

            if hasattr(self, 'monitor'):
                await self.monitor.add_transaction(transaction)

            raise