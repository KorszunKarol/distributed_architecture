"""WebSocket client for node monitoring."""
import asyncio
import json
import logging
import websockets
from typing import Dict, Any, Optional, Callable
from datetime import datetime

class NodeWebSocketClient:
    def __init__(self, node_id: str, layer: int, websocket_url: str = "ws://localhost:8000"):
        self.websocket_url = websocket_url + "/ws"
        self.node_id = node_id
        self.layer = layer
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.last_sync_time = None
        self.update_count = 0
        self._logger = logging.getLogger(f"websocket.{node_id}")
        self._closed = False
        self._reconnect_task = None
        self._send_state_task = None
        self._get_current_data: Callable[[], Dict[str, Any]] = lambda: {}
        self._get_operation_log: Callable[[], list] = lambda: []

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
        retry_count = 0
        while not self._closed:
            try:
                if not self.is_connected:
                    self._logger.info(f"Connecting to WebSocket server at {self.websocket_url}")
                    self.websocket = await websockets.connect(self.websocket_url)
                    initial_state = await self._gather_node_state()
                    await self.websocket.send(json.dumps(initial_state))
                    self.is_connected = True
                    retry_count = 0
                    self._logger.info("Successfully connected to WebSocket server")
                await asyncio.sleep(0.1)  # Check connection status more frequently
            except Exception as e:
                self._logger.error(f"WebSocket connection error: {e}")
                self.is_connected = False
                retry_count += 1
                await asyncio.sleep(min(1 * retry_count, 5))  # Exponential backoff up to 5 seconds

    async def _send_state_periodically(self):
        """Send node state periodically."""
        while not self._closed:
            try:
                if self.is_connected and self.websocket:
                    state = await self._gather_node_state()
                    if state["current_data"]:  # Only send if we have data
                        self._logger.debug(f"Sending state update: {state}")
                        await self.websocket.send(json.dumps(state))
                await asyncio.sleep(0.1)  # Send state more frequently
            except websockets.exceptions.ConnectionClosed:
                self._logger.warning("WebSocket connection closed")
                self.is_connected = False
            except Exception as e:
                self._logger.error(f"Error sending state: {e}")
                self.is_connected = False
            finally:
                await asyncio.sleep(0.1)

    async def _gather_node_state(self) -> Dict[str, Any]:
        """Gather current node state."""
        try:
            current_data = await self._get_current_data()
            return {
                "node_id": self.node_id,
                "layer": self.layer,
                "timestamp": datetime.now().isoformat(),
                "is_connected": self.is_connected,
                "last_sync_time": self.last_sync_time,
                "update_count": self.update_count,
                "current_data": current_data
            }
        except Exception as e:
            self._logger.error(f"Error gathering node state: {e}")
            return {
                "node_id": self.node_id,
                "layer": self.layer,
                "timestamp": datetime.now().isoformat(),
                "is_connected": False,
                "last_sync_time": None,
                "update_count": self.update_count,
                "current_data": {}
            }

    def update_sync_time(self):
        """Update the last sync time."""
        self.last_sync_time = datetime.now().isoformat()

    def increment_update_count(self):
        """Increment the update counter."""
        self.update_count += 1