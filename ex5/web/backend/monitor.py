from dataclasses import dataclass, asdict
from typing import Dict, List
import asyncio
from fastapi import WebSocket
import json

@dataclass
class NodeState:
    node_id: str
    layer: int
    update_count: int
    current_data: List[Dict]
    last_update: float

    def to_dict(self):
        return asdict(self)

class NodeMonitor:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.node_states: Dict[str, NodeState] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send current state immediately after connection
        state_dict = {
            node_id: state.to_dict()
            for node_id, state in self.node_states.items()
        }
        try:
            await websocket.send_json({
                'nodes': state_dict,
                'timestamp': asyncio.get_event_loop().time()
            })
        except Exception as e:
            print(f"Error sending initial state: {e}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_state(self):
        if not self.active_connections:
            return

        state_dict = {
            node_id: state.to_dict()
            for node_id, state in self.node_states.items()
        }

        for connection in self.active_connections:
            try:
                await connection.send_json({
                    'nodes': state_dict,
                    'timestamp': asyncio.get_event_loop().time()
                })
            except Exception as e:
                print(f"Error broadcasting: {e}")
                await self.disconnect(connection)

    async def update_node_state(self, node_id: str, state: NodeState):
        self.node_states[node_id] = state
        await self.broadcast_state()