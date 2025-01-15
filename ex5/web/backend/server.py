from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any, Set
import json
import logging
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket.server")

app = FastAPI()

# Store connected monitoring clients (frontend connections)
monitoring_clients: Set[WebSocket] = set()

# Store connected node clients
node_clients: Dict[str, WebSocket] = {}

# Store the latest state of each node
node_states: Dict[str, Dict] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

async def broadcast_node_state(node_id: str):
    """Broadcast all node states to all monitoring clients."""
    disconnected_clients = set()

    for client in monitoring_clients:
        try:
            await client.send_json(node_states)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            disconnected_clients.add(client)

    # Remove disconnected clients
    monitoring_clients.difference_update(disconnected_clients)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        # Wait for the first message to determine client type
        first_message = await websocket.receive_text()
        try:
            data = json.loads(first_message)

            if 'node_id' in data:
                # This is a node connection
                node_id = data['node_id']
                logger.info(f"Node {node_id} connected")
                node_clients[node_id] = websocket

                # Store and broadcast initial state
                node_states[node_id] = data
                await broadcast_node_state(node_id)

                # Handle subsequent node updates
                try:
                    while True:
                        message = await websocket.receive_text()
                        data = json.loads(message)
                        node_states[node_id] = data
                        await broadcast_node_state(node_id)
                except WebSocketDisconnect:
                    logger.info(f"Node {node_id} disconnected")
                    node_clients.pop(node_id, None)
                finally:
                    # Mark node as disconnected in state
                    if node_id in node_states:
                        node_states[node_id]['is_connected'] = False
                        await broadcast_node_state(node_id)

            elif data.get('type') == 'monitor':
                # This is a monitoring client (frontend)
                logger.info("Monitor client connected")
                monitoring_clients.add(websocket)

                # Send current state of all nodes as a single object
                logger.info(f"Sending initial state to monitor: {node_states}")
                await websocket.send_json(node_states)

                # Keep connection alive
                try:
                    while True:
                        await websocket.receive_text()
                except WebSocketDisconnect:
                    logger.info("Monitor client disconnected")
                finally:
                    monitoring_clients.remove(websocket)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in first message: {first_message}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in monitoring_clients:
            monitoring_clients.remove(websocket)

@app.get("/nodes")
async def get_nodes():
    """Get current state of all nodes."""
    return node_states

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)