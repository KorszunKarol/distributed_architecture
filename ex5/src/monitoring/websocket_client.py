import logging
import json
import time
from websockets.client import connect

class WebSocketClient:
    def __init__(self, node_id: str, layer: int):
        self.node_id = node_id
        self.layer = layer
        self.update_count = 0
        self.last_sync_time = None
        self.is_connected = True
        self._logger = logging.getLogger(f"websocket.{node_id}")

    def increment_update_count(self):
        self.update_count += 1

    def reset_update_count(self):
        self.update_count = 0

    def update_sync_time(self):
        self.last_sync_time = time.strftime("%Y-%m-%dT%H:%M:%S.%f")

    async def start(self):
        self._logger.info(f"Starting WebSocket client for node {self.node_id}")
        try:
            self.ws_url = f"ws://localhost:8000/ws"
            self._logger.info(f"Connecting to WebSocket server at {self.ws_url}")
            self.websocket = await connect(self.ws_url)
            await self._send_initial_state()
            self._logger.info("Successfully connected to WebSocket server")
        except Exception as e:
            self._logger.error(f"Failed to connect to WebSocket server: {e}")
            raise

    async def stop(self):
        self._logger.info(f"Stopping WebSocket client for node {self.node_id}")
        if hasattr(self, 'websocket'):
            await self.websocket.close()