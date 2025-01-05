from src.transaction.parser import TransactionParser
from src.proto import replication_pb2

def main():
    parser = TransactionParser()

    print("\nAvailable in replication_pb2:")
    print([attr for attr in dir(replication_pb2) if not attr.startswith('_')])

    print("\nOperation fields:")
    op = replication_pb2.Operation()
    print(op.DESCRIPTOR.fields_by_name)

    print("\nOperation message definition:")
    print(op.DESCRIPTOR)

if __name__ == "__main__":
    main()