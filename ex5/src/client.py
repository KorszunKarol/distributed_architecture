import asyncio
import grpc
from typing import List
from transaction.parser import TransactionParser
from proto import replication_pb2, replication_pb2_grpc

class Client:
    """Client for executing transactions in the distributed system."""

    def __init__(self, transaction_file: str, core_addresses: List[str]):
        """Initialize client with transaction file and core node addresses.

        Args:
            transaction_file: Path to file containing transactions
            core_addresses: List of core node addresses
        """
        self.transaction_file = transaction_file
        self.core_addresses = core_addresses
        self.parser = TransactionParser()
        self.stubs = {}

    async def connect(self):
        """Establish connections to core nodes."""
        for addr in self.core_addresses:
            channel = grpc.aio.insecure_channel(addr)
            self.stubs[addr] = replication_pb2_grpc.NodeServiceStub(channel)

    async def execute_transaction(self, transaction: replication_pb2.Transaction):
        """Execute a single transaction.

        Args:
            transaction: Transaction to execute
        """
        # For update transactions, use first core node
        stub = self.stubs[self.core_addresses[0]]
        try:
            response = await stub.ExecuteTransaction(transaction)
            return response
        except Exception as e:
            print(f"Error executing transaction: {e}")
            return None

    async def run(self):
        """Read and execute transactions from file."""
        await self.connect()

        with open(self.transaction_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    transaction = self.parser.parse_transaction(line)
                    self.parser.validate_transaction(transaction)
                    response = await self.execute_transaction(transaction)
                    print(f"Transaction executed: {line}")
                    print(f"Response: {response}")
                except ValueError as e:
                    print(f"Invalid transaction '{line}': {e}")
                except Exception as e:
                    print(f"Error processing transaction '{line}': {e}")

if __name__ == "__main__":
    # Example usage
    CORE_ADDRESSES = [
        'localhost:50051',
        'localhost:50052',
        'localhost:50053'
    ]

    client = Client("transactions.txt", CORE_ADDRESSES)
    asyncio.run(client.run())