"""Test script to verify WebSocket monitoring functionality."""
import asyncio
import logging
from src.node.core_node import CoreNode
import os

logging.basicConfig(level=logging.INFO)

async def main():
    # Create a test log directory
    log_dir = "test_logs"
    os.makedirs(log_dir, exist_ok=True)

    # Create a test core node
    node = CoreNode(
        node_id="test_node",
        log_dir=log_dir,
        port=5000,
        peer_addresses=[],
        is_first_node=True
    )

    try:
        # Start the node (this will also start the WebSocket client)
        await node.start()

        # Keep the node running for testing
        print("Node is running. Press Ctrl+C to stop...")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping node...")
    finally:
        await node.stop()

if __name__ == "__main__":
    asyncio.run(main())