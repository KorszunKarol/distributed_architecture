"""Manual test for the replication system demonstrating multi-layer architecture."""
import asyncio
import logging
from pathlib import Path
import sys
from typing import List
from src.node.core_node import CoreNode
from src.node.base_node import BaseNode
from src.node.first_layer_node import FirstLayerNode
from src.node.second_layer_node import SecondLayerNode
from src.proto import replication_pb2
import time

logger = logging.getLogger("manual_test")

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create detailed formatter
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler - captures everything
    file_handler = logging.FileHandler("logs/system.log", mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Console handler - mirrors everything to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(detailed_formatter)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    loggers = [
        "manual_test",
        "core_node",
        "first_layer_node",
        "second_layer_node",
        "replication",
        "store",
        "grpc"
    ]

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = True

    # Capture stdout and stderr
    class StreamToLogger:
        def __init__(self, logger, level):
            self.logger = logger
            self.level = level
            self.linebuf = ''

        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.level, line.rstrip())

        def flush(self):
            pass

    # Replace stdout and stderr with our logging versions
    sys.stdout = StreamToLogger(root_logger, logging.INFO)
    sys.stderr = StreamToLogger(root_logger, logging.ERROR)

    # Log uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    # Log startup
    root_logger.info("Logging system initialized")
    root_logger.info(f"Log files will be written to: {log_dir.absolute()}")

async def execute_transaction(node: BaseNode, tx_str: str):
    """Execute a transaction described by a string."""
    logger.info(f"Executing transaction: {tx_str}",
                extra={'node_id': node.node_id, 'transaction': tx_str})

    # Parse transaction type
    operations = []
    tx_type = replication_pb2.Transaction.READ_ONLY  # Default to read-only

    # Split transaction into operations
    ops = tx_str.split(", ")

    for op in ops:
        if op.startswith("b"):  # Begin transaction
            continue
        elif op.startswith("c"):  # Commit transaction
            continue
        elif op.startswith("w"):  # Write operation
            tx_type = replication_pb2.Transaction.UPDATE
            # Parse write operation w(key,value)
            key, value = map(int, op[2:-1].split(','))
            operations.append(
                replication_pb2.Operation(
                    type=replication_pb2.Operation.WRITE,
                    key=key,
                    value=value,
                    timestamp=int(time.time())
                )
            )
        elif op.startswith("r"):  # Read operation
            # Parse read operation r(key)
            key = int(op[2:-1])  # Remove r( and )
            operations.append(
                replication_pb2.Operation(
                    type=replication_pb2.Operation.READ,
                    key=key,
                    timestamp=int(time.time())
                )
            )

    # Create and execute transaction
    tx = replication_pb2.Transaction(
        type=tx_type,
        operations=operations
    )

    try:
        response = await node.ExecuteTransaction(tx, None)
        logger.info(f"Transaction response: {response}",
                   extra={'node_id': node.node_id, 'transaction': tx_str})
        return response
    except Exception as e:
        logger.error(f"Transaction failed: {e}",
                    extra={'node_id': node.node_id, 'transaction': tx_str})
        raise

async def start_nodes_in_order(nodes: list) -> None:
    """Start nodes in the correct order and wait for each to be ready."""
    for node in nodes:
        extra = {'node_id': node.node_id, 'transaction': 'STARTUP'}
        logger.info(f"Starting node {node.node_id}", extra=extra)
        await node.start()
        await node.wait_for_ready()
        logger.info(f"Node {node.node_id} is ready", extra=extra)
        await asyncio.sleep(0.1)

async def main():
    # Create second layer nodes (C1, C2)
    c2 = SecondLayerNode("C2", "logs/c2", 5007, is_primary=False)
    c1 = SecondLayerNode("C1", "logs/c1", 5006, is_primary=True,
                         backup_addresses=["localhost:5007"])

    # Create first layer nodes (B1, B2)
    b2 = FirstLayerNode("B2", "logs/b2", 5005, is_primary=False)
    b1 = FirstLayerNode("B1", "logs/b1", 5004, is_primary=True,
                        backup_address="localhost:5005",
                        second_layer_address="localhost:5006")

    # Create core layer nodes (A1, A2, A3)
    a3 = CoreNode("A3", "logs/a3", 5003,
                  peer_addresses=["localhost:5001", "localhost:5002"])
    a2 = CoreNode("A2", "logs/a2", 5002,
                  peer_addresses=["localhost:5001", "localhost:5003"])
    a1 = CoreNode("A1", "logs/a1", 5001,
                  peer_addresses=["localhost:5002", "localhost:5003"],
                  is_first_node=True,
                  first_layer_address="localhost:5004")

    # Start nodes in correct order
    nodes = [c2, c1, b2, b1, a3, a2, a1]
    await start_nodes_in_order(nodes)

    try:
        logger.info("=== Starting replication system test ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'START'})

        # Test update transactions
        logger.info("=== Testing update transactions to core layer ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'SCENARIO_1'})

        # Write operations
        write_txs = [
            "b, w(0,10), c",
            "b, w(5,15), c",
            "b, w(10,20), c"
        ]
        for tx in write_txs:
            await execute_transaction(a1, tx)
            await asyncio.sleep(1)

        # Read operations to verify
        read_txs = [
            "b, r(0), c",  # Single read
            "b, r(5), c",  # Single read
            "b, r(10), c"  # Single read
        ]

        # Test reads from different layers
        for tx in read_txs:
            logger.info("Reading from different layers:",
                       extra={'node_id': 'SYSTEM', 'transaction': 'READ_TEST'})
            await execute_transaction(a1, tx)  # Core layer
            await execute_transaction(b1, tx)  # First layer
            await execute_transaction(c1, tx)  # Second layer
            await asyncio.sleep(1)

    finally:
        logger.info("=== Shutting down replication system ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'SHUTDOWN'})
        # Stop all nodes in reverse order
        for node in reversed(nodes):
            extra = {'node_id': node.node_id, 'transaction': 'SHUTDOWN'}
            await node.stop()
            logger.info(f"Stopped node {node.node_id}", extra=extra)

if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())