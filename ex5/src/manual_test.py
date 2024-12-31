"""Manual test script for the distributed system."""
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os
import time
from src.node.core_node import CoreNode
from src.node.first_layer_node import FirstLayerNode
from src.node.second_layer_node import SecondLayerNode
from src.proto import replication_pb2

# Remove the basic logging config
# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manual_test")

# Setup logging
def setup_logging():
    """Setup logging to both file and terminal."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup file handler
    file_handler = RotatingFileHandler(
        'logs/system.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def setup_log_dirs():
    """Create log directories if they don't exist."""
    log_dirs = [
        "logs/core/a1",
        "logs/core/a2",
        "logs/core/a3",
        "logs/first/b1",
        "logs/first/b2",
        "logs/second/c1",
        "logs/second/c2"
    ]
    for dir_path in log_dirs:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Created log directory: {dir_path}")

async def test_write_transaction(node: CoreNode, key: int, value: int):
    """Execute a write transaction on a core node."""
    try:
        operation = replication_pb2.Operation(
            type=replication_pb2.Operation.WRITE,
            key=key,
            value=value,
            timestamp=int(time.time())
        )

        tx = replication_pb2.Transaction(
            type=replication_pb2.Transaction.UPDATE,
            operations=[operation]
        )

        response = await node.ExecuteTransaction(tx, None)
        if not response.success:
            logger.error(f"Write failed: {response.error_message}")
        return response.success
    except Exception as e:
        logger.error(f"Write transaction error: {e}")
        return False

async def test_read_transaction(node: CoreNode, key: int):
    """Execute a read transaction on any node."""
    operation = replication_pb2.Operation(
        type=replication_pb2.Operation.READ,
        key=key,  # Already an integer
        timestamp=int(time.time())
    )

    tx = replication_pb2.Transaction(
        type=replication_pb2.Transaction.READ_ONLY,
        operations=[operation]
    )

    response = await node.ExecuteTransaction(tx, None)
    logger.info(f"Read response: {response}")
    return response.results[0] if response.results else None

async def main():
    # Setup logging first
    setup_logging()
    setup_log_dirs()

    nodes = []
    try:
        # Create core layer nodes
        a1 = CoreNode(
            "A1",
            "logs/core/a1",
            5001,
            peer_addresses=["localhost:5002", "localhost:5003"],  # Other core nodes
            is_first_node=True,
            first_layer_address="localhost:5004"
        )

        # Create first layer nodes
        b1 = FirstLayerNode(
            "B1",
            "logs/first/b1",
            5004,
            is_primary=True,
            backup_address="localhost:5005",
            second_layer_address="localhost:5006"
        )

        # Create second layer nodes
        c1 = SecondLayerNode(
            "C1",
            "logs/second/c1",
            5006,
            is_primary=True,
            backup_address="localhost:5007"
        )

        nodes = [a1, b1, c1]

        # Start nodes in order
        for node in nodes:
            await node.start()
            await asyncio.sleep(1)  # Give each node time to start
            logger.info(f"Started node {node.node_id}")

        # Test writes with integers
        for i in range(12):
            success = await test_write_transaction(a1, i, i*100)  # Use integers directly
            logger.info(f"Write {i} success: {success}")
            await asyncio.sleep(1)

        # Test reads
        await asyncio.sleep(5)
        for key in [0, 5, 10]:
            logger.info("Reading from different layers:")
            a1_value = await test_read_transaction(a1, key)
            b1_value = await test_read_transaction(b1, key)
            c1_value = await test_read_transaction(c1, key)
            logger.info(f"key{key}: A1={a1_value}, B1={b1_value}, C1={c1_value}")

    finally:
        # Clean shutdown
        for node in nodes:
            try:
                await node.stop()
                logger.info(f"Stopped node {node.node_id}")
            except Exception as e:
                logger.error(f"Error stopping node: {e}")

if __name__ == "__main__":
    asyncio.run(main())