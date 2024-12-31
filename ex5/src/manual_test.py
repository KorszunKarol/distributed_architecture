"""Manual test script for the distributed system."""
import asyncio
import logging
from src.node.core_node import CoreNode
from src.node.first_layer_node import FirstLayerNode
from src.node.second_layer_node import SecondLayerNode
from src.proto import replication_pb2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manual_test")

async def test_write_transaction(node: CoreNode, key: str, value: str):
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

async def test_read_transaction(node: CoreNode, key: str):
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
    # Create nodes
    a1 = CoreNode("A1", "logs/a1", 5001, [], is_first_node=True, first_layer_address="localhost:5004")
    b1 = FirstLayerNode("B1", "logs/b1", 5004, is_primary=True, backup_address="localhost:5005", second_layer_address="localhost:5006")
    c1 = SecondLayerNode("C1", "logs/c1", 5006, is_primary=True, backup_address="localhost:5007")

    # Start nodes
    for node in [a1, b1, c1]:
        await node.start()
        logger.info(f"Started node {node.node_id}")

    try:
        # Test writes
        for i in range(12):  # More than 10 to trigger propagation
            success = await test_write_transaction(a1, f"key{i}", f"value{i}")
            logger.info(f"Write {i} success: {success}")
            await asyncio.sleep(1)  # Give time for propagation

        # Test reads from different layers
        await asyncio.sleep(5)  # Wait for propagation
        for key in ["key0", "key5", "key10"]:
            logger.info("Reading from different layers:")
            a1_value = await test_read_transaction(a1, key)
            b1_value = await test_read_transaction(b1, key)
            c1_value = await test_read_transaction(c1, key)
            logger.info(f"{key}: A1={a1_value}, B1={b1_value}, C1={c1_value}")

    finally:
        # Stop nodes
        for node in [a1, b1, c1]:
            await node.stop()
            logger.info(f"Stopped node {node.node_id}")

if __name__ == "__main__":
    asyncio.run(main())