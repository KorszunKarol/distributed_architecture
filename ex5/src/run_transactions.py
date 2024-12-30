"""Script to run transactions from a file."""
import asyncio
from client.transaction_client import TransactionClient

# Configuration
CORE_ADDRESSES = [
    'localhost:50051',  # A1
    'localhost:50052',  # A2
    'localhost:50053'   # A3
]

LAYER_ADDRESSES = [
    CORE_ADDRESSES,                         # Layer 0 (Core)
    ['localhost:50054', 'localhost:50055'], # Layer 1 (B1, B2)
    ['localhost:50056', 'localhost:50057']  # Layer 2 (C1, C2)
]

async def main():
    """Run transactions from the transaction file."""
    client = TransactionClient(CORE_ADDRESSES, LAYER_ADDRESSES)

    print("Starting transaction execution...")
    await client.run_transaction_file('transactions.txt')
    print("\nTransaction execution completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExecution interrupted by user")