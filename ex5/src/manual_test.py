"""Manual test for the replication system demonstrating multi-layer architecture."""
import asyncio
import logging
from pathlib import Path
from src.node.core_node import CoreNode
from src.node.first_layer_node import FirstLayerNode
from src.node.second_layer_node import SecondLayerNode
from src.node.base_node import BaseNode  # Also needed for execute_transaction
from src.transaction.parser import TransactionParser
import sys
logger = logging.getLogger("manual_test")

def setup_logging():
    """Set up logging configuration."""
    root_logger = logging.getLogger()
    root_logger.handlers = []

    # Clean up old logs and data files
    log_dir = Path("logs")
    if log_dir.exists():
        # Remove all log files and directories
        for item in log_dir.glob("**/*"):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                for subitem in item.glob("*"):
                    subitem.unlink()
                item.rmdir()
        log_dir.rmdir()

    # Remove any .jsonl or version_history files in the current directory
    for file in Path(".").glob("*.jsonl"):
        file.unlink()
    for file in Path(".").glob("*version_history*"):
        file.unlink()

    # Create fresh log directories
    log_dir.mkdir(exist_ok=True, parents=True)
    for node in ['a1', 'a2', 'a3', 'b1', 'b2', 'c1', 'c2']:
        node_dir = log_dir / node
        node_dir.mkdir(exist_ok=True, parents=True)

    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    system_log = log_dir / "system.log"
    file_handler = logging.FileHandler(str(system_log), mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(detailed_formatter)

    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    root_logger.info("Logging system initialized")
    root_logger.info(f"Log files will be written to: {log_dir.absolute()}")

async def start_nodes_in_order(nodes: list) -> None:
    """Start nodes in the correct order and wait for each to be ready."""
    for node in nodes:
        extra = {'node_id': node.node_id, 'transaction': 'STARTUP'}
        logger.info(f"Starting node {node.node_id}", extra=extra)
        await node.start()
        await node.wait_for_ready()
        logger.info(f"Node {node.node_id} is ready", extra=extra)
        await asyncio.sleep(0.1)

async def execute_transaction(node: BaseNode, tx_str: str) -> None:
    """Execute a transaction on a node."""
    try:
        logger.info("")
        logger.info(f"Parsing transaction: {tx_str}")

        parser = TransactionParser()
        tx = parser.parse(tx_str)

        logger.info(f"Parsed transaction: {tx}")

        response = await node.ExecuteTransaction(tx, None)

        if response and response.results:
            logger.info("Read results:")
            for result in response.results:
                logger.info(f"  key={result.key}: value={result.value} (version={result.version})")
    except Exception as e:
        logger.error(f"Transaction failed: {e}")
        raise

def cleanup_files():
    """Clean up any remaining data files."""
    for file in Path(".").glob("*.jsonl"):
        file.unlink()
    for file in Path(".").glob("*version_history*"):
        file.unlink()

async def main():
    # Initialize nodes
    c2 = SecondLayerNode("C2", "logs/c2", 5007, is_primary=False)
    c1 = SecondLayerNode("C1", "logs/c1", 5006, is_primary=True,
                         backup_addresses=["localhost:5007"])

    b2 = FirstLayerNode(
        node_id="B2",
        port=5005,
        is_primary=False
    )
    b1 = FirstLayerNode(
        node_id="B1",
        port=5004,
        is_primary=True,
        backup_addresses=["localhost:5005"],
        second_layer_address="localhost:5006"
    )

    a3 = CoreNode("A3", "logs/a3", 5003,
                  peer_addresses=["localhost:5001", "localhost:5002"])
    a2 = CoreNode("A2", "logs/a2", 5002,
                  peer_addresses=["localhost:5001", "localhost:5003"])
    a1 = CoreNode("A1", "logs/a1", 5001,
                  peer_addresses=["localhost:5002", "localhost:5003"],
                  is_first_node=True,
                  first_layer_address="localhost:5004")

    nodes = [c2, c1, b2, b1, a3, a2, a1]
    await start_nodes_in_order(nodes)

    try:
        logger.info("=== Starting replication system test ===")

        # Initialize parser
        parser = TransactionParser()

        # Read transactions from file
        tx_file = Path("transactions.txt")
        if not tx_file.exists():
            raise FileNotFoundError("transactions.txt not found")

        transactions = tx_file.read_text().splitlines()

        for i, tx_line in enumerate(transactions, 1):
            if not tx_line.strip():  # Skip empty lines
                continue

            logger.info(f"\n=== Executing transaction {i}: {tx_line} ===\n")

            # Parse transaction
            tx = parser.parse(tx_line)

            # Select target node based on layer
            target_node = None
            if tx.target_layer == 0:
                target_node = a1
            elif tx.target_layer == 1:
                target_node = b1
            elif tx.target_layer == 2:
                target_node = c1
            else:
                logger.error(f"Invalid target layer: {tx.target_layer}")
                continue

            # Execute transaction on target node
            response = await target_node.ExecuteTransaction(tx, None)  # Pass None as context

            # Log results
            if response and response.results:
                logger.info("Read results:")
                for result in response.results:
                    logger.info(f"  key={result.key}: value={result.value} (version={result.version})")

            # Wait 1 second between transactions
            await asyncio.sleep(1.0)  # Changed from 0.1 to 1.0

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error executing transactions: {e}")
        raise
    finally:
        logger.info("=== Shutting down replication system ===")
        for node in reversed(nodes):
            await node.stop()
        cleanup_files()

if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())