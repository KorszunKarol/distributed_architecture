"""Client for executing transactions from a file."""
import asyncio
import grpc
from typing import List
from src.transaction.parser import TransactionParser, Operation, OperationType
from src.proto import replication_pb2, replication_pb2_grpc

class TransactionClient:
    """Client for executing transactions from a file."""

    def __init__(self, core_addresses: List[str], layer_addresses: List[List[str]]):
        """
        Initialize the transaction client.

        Args:
            core_addresses: List of addresses for core layer nodes
            layer_addresses: List of lists of addresses for each layer (including core)
        """
        self.core_addresses = core_addresses
        self.layer_addresses = layer_addresses
        self.parser = TransactionParser()

    async def execute_transaction(self, transaction_str: str) -> bool:
        """
        Execute a single transaction.

        Args:
            transaction_str: Transaction string from file

        Returns:
            bool: True if transaction executed successfully
        """
        try:
            operations = self.parser.parse_transaction(transaction_str)
            if not operations:
                return False

            # Determine transaction type and target layer
            begin_op = operations[0]
            if begin_op.type != OperationType.BEGIN:
                raise ValueError("Transaction must start with begin operation")

            is_readonly = begin_op.layer is not None
            target_layer = begin_op.layer if is_readonly else 0

            # Select appropriate node address
            if is_readonly:
                addresses = self.layer_addresses[target_layer]
                # Round-robin selection for read-only transactions
                address = addresses[hash(transaction_str) % len(addresses)]
            else:
                # For update transactions, always use core layer
                address = self.core_addresses[hash(transaction_str) % len(self.core_addresses)]

            # Create gRPC transaction
            grpc_ops = []
            for op in operations[1:-1]:  # Skip begin and commit
                if op.type == OperationType.READ:
                    grpc_ops.append(
                        replication_pb2.Operation(
                            type=replication_pb2.Operation.READ,
                            key=op.key
                        )
                    )
                elif op.type == OperationType.WRITE:
                    grpc_ops.append(
                        replication_pb2.Operation(
                            type=replication_pb2.Operation.WRITE,
                            key=op.key,
                            value=op.value
                        )
                    )

            transaction = replication_pb2.Transaction(
                type=replication_pb2.Transaction.READ_ONLY if is_readonly else replication_pb2.Transaction.UPDATE,
                target_layer=target_layer,
                operations=grpc_ops
            )

            # Execute transaction
            async with grpc.aio.insecure_channel(address) as channel:
                stub = replication_pb2_grpc.NodeServiceStub(channel)
                response = await stub.ExecuteTransaction(transaction)
                return response.success

        except Exception as e:
            print(f"Error executing transaction: {e}")
            return False

    async def run_transaction_file(self, filename: str):
        """
        Execute all transactions from a file.

        Args:
            filename: Path to transaction file
        """
        try:
            with open(filename, 'r') as f:
                transactions = f.readlines()

            for transaction in transactions:
                transaction = transaction.strip()
                if not transaction:
                    continue

                print(f"\nExecuting: {transaction}")
                success = await self.execute_transaction(transaction)
                print(f"Response: success: {success}")

                # Small delay between transactions
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error reading transaction file: {e}")