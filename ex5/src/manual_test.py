"""Manual test script for the distributed system."""
import asyncio
import logging
from pathlib import Path
import os
import sys

from src.node.core_node import CoreNode
from src.node.first_layer_node import FirstLayerNode
from src.node.second_layer_node import SecondLayerNode
from src.proto import replication_pb2

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Clear/delete existing log file
log_file = log_dir / "system.log"
if log_file.exists():
    log_file.unlink()

# Configure logging - Fix double logging by using only one handler per destination
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)  # Remove stderr handler to avoid duplicates
    ]
)

logger = logging.getLogger("manual_test")

async def test_write_transaction(node: CoreNode, key: int, value: int):
    """Execute a write transaction on a core node."""
    tx = replication_pb2.Transaction(
        type=replication_pb2.Transaction.UPDATE,
        operations=[
            replication_pb2.Operation(
                type=replication_pb2.Operation.WRITE,
                key=key,
                value=value
            )
        ]
    )
    response = await node.ExecuteTransaction(tx, None)
    logger.info(f"Write response: {response}")
    return response.success

async def test_read_transaction(node, key: int):
    """Execute a read transaction on any node."""
    tx = replication_pb2.Transaction(
        type=replication_pb2.Transaction.READ_ONLY,
        operations=[
            replication_pb2.Operation(
                type=replication_pb2.Operation.READ,
                key=key
            )
        ]
    )
    response = await node.ExecuteTransaction(tx, None)
    logger.info(f"Read response: {response}")
    return response.results[0] if response.results else None

async def main():
    # Create core layer nodes (3 nodes)
    a1 = CoreNode("A1", "logs/a1", 5001, 
                  peer_addresses=["localhost:5002", "localhost:5003"],
                  is_first_node=True, 
                  first_layer_address="localhost:5004")
    a2 = CoreNode("A2", "logs/a2", 5002,
                  peer_addresses=["localhost:5001", "localhost:5003"])
    a3 = CoreNode("A3", "logs/a3", 5003,
                  peer_addresses=["localhost:5001", "localhost:5002"])

    # Create first layer nodes (2 nodes)
    b1 = FirstLayerNode("B1", "logs/b1", 5004,
                        is_primary=True,
                        backup_address="localhost:5005",
                        second_layer_address="localhost:5006")
    b2 = FirstLayerNode("B2", "logs/b2", 5005,
                        is_primary=False)

    # Create second layer nodes (2 nodes)
    c1 = SecondLayerNode("C1", "logs/c1", 5006,
                         is_primary=True,
                         backup_addresses=["localhost:5007"])
    c2 = SecondLayerNode("C2", "logs/c2", 5007,
                         is_primary=False)

    # Start all nodes
    nodes = [a1, a2, a3, b1, b2, c1, c2]
    for node in nodes:
        await node.start()
        logger.info(f"Started node {node.node_id}")

    try:
        # Test writes
        for i in range(12):  # More than 10 to trigger propagation
            success = await test_write_transaction(a1, i, i * 100)
            logger.info(f"Write {i} success: {success}")
            await asyncio.sleep(1)  # Give time for propagation

        # Test reads from different layers
        await asyncio.sleep(5)  # Wait for propagation
        for key in [0, 5, 10]:
            logger.info("Reading from different layers:")
            # Read from each layer
            a_value = await test_read_transaction(a1, key)  # Core layer
            b_value = await test_read_transaction(b1, key)  # First layer
            c_value = await test_read_transaction(c1, key)  # Second layer
            logger.info(f"key{key}: Core={a_value}, FirstLayer={b_value}, SecondLayer={c_value}")

    finally:
        # Stop all nodes
        for node in nodes:
            await node.stop()
            logger.info(f"Stopped node {node.node_id}")

if __name__ == "__main__":
    asyncio.run(main())