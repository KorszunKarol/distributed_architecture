"""Transaction processing module for the distributed system."""
import logging
from dataclasses import dataclass
from typing import List, Optional
from src.proto import replication_pb2
from src.transaction.parser import TransactionParser, Operation, OperationType

@dataclass
class ParsedOperation:
    """Represents a parsed operation from a transaction string."""
    op_type: str  # 'r' for read, 'w' for write
    key: int
    value: Optional[int] = None

@dataclass
class ParsedTransaction:
    """Represents a parsed transaction from a string."""
    target_layer: int
    operations: List[ParsedOperation]
    is_read_only: bool

class TransactionProcessor:
    """Handles transaction processing using parsed operations."""

    def __init__(self):
        """Initialize processor with a parser."""
        self.parser = TransactionParser()

    def process_transaction(self, tx_str: str) -> replication_pb2.Transaction:
        """
        Process a transaction string into a gRPC transaction message.

        Args:
            tx_str: Transaction string to process

        Returns:
            A gRPC Transaction message
        """
        operations = self.parser.parse(tx_str)

        # Extract transaction metadata
        target_layer = 0
        is_read_only = True
        grpc_operations = []

        for op in operations:
            if op.type == OperationType.BEGIN:
                target_layer = op.layer if op.layer is not None else 0

            elif op.type == OperationType.READ:
                grpc_operations.append(replication_pb2.Operation(
                    type=replication_pb2.Operation.READ,
                    key=op.key
                ))

            elif op.type == OperationType.WRITE:
                is_read_only = False
                grpc_operations.append(replication_pb2.Operation(
                    type=replication_pb2.Operation.WRITE,
                    key=op.key,
                    value=op.value
                ))

        return replication_pb2.Transaction(
            type=(replication_pb2.Transaction.READ_ONLY
                  if is_read_only else replication_pb2.Transaction.UPDATE),
            target_layer=target_layer,
            operations=grpc_operations
        )