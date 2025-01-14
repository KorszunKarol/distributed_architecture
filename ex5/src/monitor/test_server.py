"""Simple WebSocket test server for monitoring."""
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket.test_server")

async def handle_client(websocket):
    """Handle incoming WebSocket connections."""
    try:
        logger.info("Client connected")
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Received state from node {data['node_id']} (layer {data['layer']}):")
                logger.info(f"  - Update count: {data['update_count']}")
                logger.info(f"  - Last sync: {data['last_sync_time']}")
                logger.info(f"  - Current data: {data['current_data']}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {message}")
    except websockets.exceptions.ConnectionClosed:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error handling client: {e}")

async def main():
    """Start the WebSocket server."""
    logger.info("Starting WebSocket test server on ws://localhost:8000")
    async with websockets.serve(handle_client, "localhost", 8000):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())