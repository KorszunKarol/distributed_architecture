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
import re
from src.transaction.parser import TransactionParser

logger = logging.getLogger("manual_test")

def setup_logging():
    """Set up logging configuration."""
    root_logger = logging.getLogger()
    root_logger.handlers = []

    log_dir = Path("logs")
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

async def read_transactions_file() -> List[str]:
    """Read transactions from transactions.txt file."""
    transactions_file = Path(__file__).parent.parent / "transactions.txt"
    logger.info(f"Reading transactions from {transactions_file}")

    try:
        with open(transactions_file, 'r') as f:
            transactions = [
                line.strip() for line in f
                if line.strip() and not line.startswith('#')
            ]
        logger.info(f"Found {len(transactions)} transactions")
        return transactions
    except FileNotFoundError:
        logger.error(f"Transactions file not found at {transactions_file}")
        raise
    except Exception as e:
        logger.error(f"Error reading transactions file: {e}")
        raise

async def main():
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
        logger.info("=== Starting replication system test ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'START'})

        transactions = await read_transactions_file()

        logger.info("=== Executing transactions from file ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'EXECUTE'})

        for i, tx_str in enumerate(transactions, 1):
            logger.info(f"\nExecuting transaction {i}/{len(transactions)}")

            if tx_str.startswith('b0'):
                target_node = a1
            elif tx_str.startswith('b1'):
                target_node = b1
            elif tx_str.startswith('b2'):
                target_node = c1
            else:
                target_node = a1

            try:
                await execute_transaction(target_node, tx_str)
                await asyncio.sleep(2.0)
            except Exception as e:
                logger.error(f"Failed to execute transaction {tx_str}: {e}")
                continue

        logger.info("=== All transactions completed ===")

        await asyncio.sleep(5)

    finally:
        logger.info("=== Shutting down replication system ===",
                   extra={'node_id': 'SYSTEM', 'transaction': 'SHUTDOWN'})
        for node in reversed(nodes):
            extra = {'node_id': node.node_id, 'transaction': 'SHUTDOWN'}
            await node.stop()
            logger.info(f"Stopped node {node.node_id}", extra=extra)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())