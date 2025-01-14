"""Simple WebSocket test server for monitoring."""
import asyncio
import websockets
import json
import logging
from typing import Set

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket.test_server")

# Store connected monitoring clients
monitoring_clients: Set[websockets.WebSocketServerProtocol] = set()

# Store the latest state of each node
node_states = {}

async def broadcast_node_state(node_id: str):
    """Broadcast a node's state to all monitoring clients."""
    if node_id not in node_states:
        return

    state = node_states[node_id]
    message = json.dumps(state)
    logger.debug(f"Broadcasting state for node {node_id} to {len(monitoring_clients)} clients")

    disconnected_clients = set()
    for client in monitoring_clients:
        try:
            await client.send(message)
            logger.debug(f"Successfully sent state to client")
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Client disconnected during broadcast")
            disconnected_clients.add(client)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            disconnected_clients.add(client)

    # Remove disconnected clients
    monitoring_clients.difference_update(disconnected_clients)

async def handle_client(websocket):
    """Handle incoming WebSocket connections."""
    try:
        # Check if this is a node connection by trying to parse the first message
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
            try:
                data = json.loads(message)
                if 'node_id' in data:
                    # This is a node connection
                    logger.info("Node connected")
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            node_id = data['node_id']

                            logger.info(f"Received state from node {node_id} (layer {data['layer']}):")
                            logger.info(f"  - Update count: {data['update_count']}")
                            logger.info(f"  - Last sync: {data['last_sync_time']}")
                            logger.info(f"  - Current data: {data['current_data']}")

                            # Store the node state
                            node_states[node_id] = data

                            # Broadcast to all monitoring clients
                            await broadcast_node_state(node_id)

                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON received: {message}")
                    return
            except json.JSONDecodeError:
                pass
        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
            pass

        # If we get here, treat it as a monitor connection
        logger.info("Monitor client connected")
        monitoring_clients.add(websocket)

        # Send current state of all nodes to the new monitor
        logger.info(f"Sending initial state of {len(node_states)} nodes to new monitor")
        for node_id, state in node_states.items():
            try:
                await websocket.send(json.dumps(state))
                logger.debug(f"Sent initial state for node {node_id}")
            except Exception as e:
                logger.error(f"Error sending initial state to monitor: {e}")
                break

        try:
            # Keep the connection alive until the client disconnects
            async for _ in websocket:
                pass  # Just keep the connection open
        except websockets.exceptions.ConnectionClosed:
            logger.info("Monitor client disconnected")
        finally:
            monitoring_clients.remove(websocket)
            logger.info("Removed monitor client from active set")

    except Exception as e:
        logger.error(f"Error handling client: {e}")
        logger.exception(e)

async def main():
    """Start the WebSocket server."""
    logger.info("Starting WebSocket test server on ws://localhost:8000")
    server = await websockets.serve(
        handle_client,
        "localhost",
        8000,
        ping_interval=20,  # Send ping every 20 seconds
        ping_timeout=10    # Wait 10 seconds for pong response
    )
    logger.info("WebSocket server is running")
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())