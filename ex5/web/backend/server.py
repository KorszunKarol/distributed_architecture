from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from monitor import NodeMonitor, NodeState
from typing import Dict, Any
import json

app = FastAPI()
monitor = NodeMonitor()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await monitor.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        monitor.disconnect(websocket)

@app.post("/node/{node_id}/state")
async def update_node_state(node_id: str, state: dict):
    """Update node state in the monitor."""
    node_state = NodeState(
        node_id=state["node_id"],
        layer=state["layer"],
        update_count=state["update_count"],
        current_data=state["current_data"],
        last_sync_time=state["last_sync_time"],
        last_sync_count=state["last_sync_count"],
        operation_log=state["operation_log"]
    )
    await monitor.update_node_state(node_id, node_state)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)