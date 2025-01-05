from dataclasses import dataclass, asdict
from typing import Dict, List
import asyncio
from fastapi import WebSocket
import json

@dataclass
class Transaction:
    timestamp: float
    command: str
    node_id: str
    status: str  # 'success' or 'failed'
    target_layer: int
    error: str = None

@dataclass
class NodeState:
    node_id: str
    layer: int
    update_count: int
    current_data: List[Dict]
    last_sync_time: float
    last_sync_count: int
    operation_log: List[Dict]
    transactions: List[Transaction]  # Add transaction history

    def to_dict(self):
        return asdict(self)

class NodeMonitor:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.node_states: Dict[str, NodeState] = {}
        self.transaction_history: List[Transaction] = []  # Global transaction history

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

    async def add_transaction(self, transaction: Transaction):
        # Add to global history
        self.transaction_history.append(transaction)

        # Add to node-specific history
        if transaction.node_id in self.node_states:
            state = self.node_states[transaction.node_id]
            state.transactions = state.transactions[-99:] + [transaction]  # Keep last 100
            await self.broadcast_state()