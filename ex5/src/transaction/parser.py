from dataclasses import dataclass
from typing import List
from proto import replication_pb2

@dataclass
class ParsedOperation:
    """Represents a parsed operation from a transaction string.

    Attributes:
        op_type: Operation type - either 'r' for read or 'w' for write
        key: The key to read or write
        value: The value to write (only for write operations)
    """
    op_type: str
    key: int
    value: int | None = None

class TransactionParser:
    """Parser for transaction strings into gRPC Transaction messages."""

    def parse_transaction(self, line: str) -> replication_pb2.Transaction:
        """Parse a transaction string into a Transaction protobuf message.

        Args:
            line: Transaction string in format: b[layer], op1, op2, ..., c
                 where operations are r(key) or w(key,value)

        Returns:
            Transaction protobuf message with parsed operations

        Raises:
            ValueError: If transaction string is malformed
        """
        parts = [p.strip() for p in line.split(',')]

        if not parts[0].startswith('b'):
            raise ValueError("Transaction must start with 'b'")

        is_readonly = len(parts[0]) > 1
        target_layer = int(parts[0][1]) if is_readonly else 0

        operations = []
        for part in parts[1:-1]:
            if part.startswith('r'):
                key = int(part[2:-1])
                operations.append(
                    replication_pb2.Operation(
                        type=replication_pb2.Operation.READ,
                        key=key
                    )
                )
            elif part.startswith('w'):
                key, value = map(int, part[2:-1].split(','))
                operations.append(
                    replication_pb2.Operation(
                        type=replication_pb2.Operation.WRITE,
                        key=key,
                        value=value
                    )
                )

        return replication_pb2.Transaction(
            type=replication_pb2.Transaction.READ_ONLY if is_readonly else replication_pb2.Transaction.UPDATE,
            target_layer=target_layer,
            operations=operations
        )

    def validate_transaction(self, transaction: replication_pb2.Transaction) -> bool:
        """Validate a parsed transaction.

        Args:
            transaction: Transaction protobuf message to validate

        Returns:
            True if transaction is valid, False otherwise

        Raises:
            ValueError: If transaction is invalid with specific reason
        """
        if transaction.type == replication_pb2.Transaction.READ_ONLY:
            if any(op.type == replication_pb2.Operation.WRITE for op in transaction.operations):
                raise ValueError("Read-only transaction cannot contain write operations")

        if transaction.target_layer > 2:
            raise ValueError("Invalid layer number")

        return True