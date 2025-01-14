"""WebSocket client for node monitoring."""
import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional
from datetime import datetime

class NodeWebSocketClient:
    def __init__(self, node_id: str, layer: int, websocket_url: str = "ws://localhost:8000"):
        self.node_id = node_id
        self.layer = layer
        self.websocket_url = websocket_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.last_sync_time = None
        self.update_count = 0
        self._logger = logging.getLogger(f"websocket.{node_id}")
        self._closed = False
        self._reconnect_task = None
        self._send_state_task = None

    async def start(self):
        """Start the WebSocket client."""
        self._logger.info(f"Starting WebSocket client for node {self.node_id}")
        self._closed = False
        self._reconnect_task = asyncio.create_task(self._maintain_connection())
        self._send_state_task = asyncio.create_task(self._send_state_periodically())

    async def stop(self):
        """Stop the WebSocket client."""
        self._logger.info(f"Stopping WebSocket client for node {self.node_id}")
        self._closed = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
        if self._send_state_task:
            self._send_state_task.cancel()
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False

    async def _maintain_connection(self):
        """Maintain WebSocket connection with reconnection logic."""
        while not self._closed:
            try:
                if not self.is_connected:
                    self._logger.info(f"Connecting to WebSocket server at {self.websocket_url}")
                    self.websocket = await websockets.connect(self.websocket_url)
                    self.is_connected = True
                    self._logger.info("Successfully connected to WebSocket server")
                await asyncio.sleep(1)  # Check connection status periodically
            except Exception as e:
                self._logger.error(f"WebSocket connection error: {e}")
                self.is_connected = False
                await asyncio.sleep(5)  # Wait before reconnecting

    async def _send_state_periodically(self):
        """Send node state periodically."""
        while not self._closed:
            try:
                if self.is_connected and self.websocket:
                    state = await self._gather_node_state()
                    await self.websocket.send(json.dumps(state))
                await asyncio.sleep(0.5)  # Send state every 0.5 seconds
            except Exception as e:
                self._logger.error(f"Error sending state: {e}")
                self.is_connected = False
                await asyncio.sleep(1)

    async def _gather_node_state(self) -> Dict[str, Any]:
        """Gather current node state."""
        return {
            "node_id": self.node_id,
            "layer": self.layer,
            "timestamp": datetime.now().isoformat(),
            "is_connected": self.is_connected,
            "last_sync_time": self.last_sync_time,
            "update_count": self.update_count,
            "current_data": await self._get_current_data()
        }

    async def _get_current_data(self) -> Dict[str, Any]:
        """Get current data from the node's store."""
        # This will be implemented by the node instance
        return {}

    def update_sync_time(self):
        """Update the last sync time."""
        self.last_sync_time = datetime.now().isoformat()

    def increment_update_count(self):
        """Increment the update counter."""
        self.update_count += 1