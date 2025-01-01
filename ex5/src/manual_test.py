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

logger = logging.getLogger("manual_test")

def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters with more detailed information
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s\n'
        'Node: %(node_id)s | Transaction: %(transaction)s\n'
        '----------------------------------------'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler - capture everything at DEBUG level
    file_handler = logging.FileHandler("logs/system.log", mode='w')  # 'w' mode to start fresh
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler - show INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Remove any existing handlers to avoid duplication
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
        "store"
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = True  # Allow propagation to root logger
    
    # Ensure all uncaught exceptions are logged
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Call the default handler for keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        root_logger.error("Uncaught exception", 
                         exc_info=(exc_type, exc_value, exc_traceback),
                         extra={'node_id': 'SYSTEM', 'transaction': 'ERROR'})
    
    sys.excepthook = handle_exception

async def execute_transaction(node: BaseNode, tx_str: str) -> None:
    """Execute a transaction from its string representation.
    
    Formats supported:
    - Read-only: "b<f>, r(30), r(49), r(69), c" where f is layer number
    - Update: "b, r(12), w(49,53), r(69), c"
    """
    extra = {'node_id': node.node_id, 'transaction': tx_str}
    logger.info(f"Executing transaction: {tx_str}", extra=extra)
    
    parts = [p.strip() for p in tx_str.split(',')]
    operations = []
    
    # Determine transaction type and target layer
    if parts[0].startswith('b<'):
        tx_type = replication_pb2.Transaction.READ_ONLY
        target_layer = int(parts[0][2:-1])
    else:
        tx_type = replication_pb2.Transaction.UPDATE
        target_layer = 0  # Core layer
    
    # Parse operations
    for op in parts[1:-1]:  # Skip begin and commit
        if op.startswith('r('):
            key = int(op[2:-1])
            operations.append(
                replication_pb2.Operation(
                    type=replication_pb2.Operation.READ,
                    key=key
                )
            )
        elif op.startswith('w('):
            key, value = map(int, op[2:-1].split(','))
            operations.append(
                replication_pb2.Operation(
                    type=replication_pb2.Operation.WRITE,
                    key=key,
                    value=value
                )
            )
    
    tx = replication_pb2.Transaction(
        type=tx_type,
        operations=operations,
        target_layer=target_layer
    )
    
    response = await node.ExecuteTransaction(tx, None)
    logger.info(f"Transaction '{tx_str}' result: {response}", extra=extra)

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
        
        # Test scenario 1: Update transactions to core layer
        logger.info("=== Testing update transactions to core layer ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'SCENARIO_1'})
        update_txs = [
            "b, w(49,53), r(49), c",
            "b, w(30,100), r(30), c",
            "b, w(69,200), r(69), c"
        ]
        for tx in update_txs:
            await execute_transaction(a1, tx)
            await asyncio.sleep(1)  # Give time for propagation

        # Wait for propagation to other layers
        logger.info("Waiting for propagation...")
        await asyncio.sleep(10)

        # Test scenario 2: Read-only transactions to different layers
        logger.info("=== Testing read-only transactions across layers ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'SCENARIO_2'})
        read_txs = [
            "b<0>, r(30), r(49), r(69), c",  # Core layer
            "b<1>, r(30), r(49), r(69), c",  # First layer
            "b<2>, r(30), r(49), r(69), c"   # Second layer
        ]
        for tx in read_txs:
            await execute_transaction(a1, tx)
            await asyncio.sleep(1)

        # Test scenario 3: More updates to demonstrate propagation
        logger.info("=== Testing propagation triggers ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'SCENARIO_3'})
        # Generate 10 updates to trigger first layer propagation
        for i in range(10):
            tx = f"b, w({i},100), c"
            await execute_transaction(a1, tx)
            await asyncio.sleep(0.5)

        # Wait and verify propagation
        logger.info("Verifying propagation across layers...",
                   extra={'node_id': 'SYSTEM', 'transaction': 'SCENARIO_4'})
        await asyncio.sleep(10)
        verify_txs = [
            "b<0>, r(0), r(5), r(9), c",  # Core layer
            "b<1>, r(0), r(5), r(9), c",  # First layer
            "b<2>, r(0), r(5), r(9), c"   # Second layer
        ]
        for tx in verify_txs:
            await execute_transaction(a1, tx)
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