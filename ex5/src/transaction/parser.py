"""Transaction parser module for handling transaction strings."""
from typing import List
from src.proto import replication_pb2

class TransactionParser:
    """Class for parsing transaction strings into protobuf Transaction messages."""

    def _parse_begin(self, op_str: str) -> int:
        """Parse BEGIN operation and return target layer if specified."""
        if op_str.startswith('b<') and op_str.endswith('>'):
            return int(op_str[2:-1])
        return 0

    def _parse_read(self, op_str: str) -> replication_pb2.Operation:
        """Parse READ operation into protobuf Operation."""
        try:
            # Extract key between r( and )
            start = op_str.index('(')
            end = op_str.rindex(')')
            key = int(op_str[start + 1:end])

            # Create operation
            op = replication_pb2.Operation()
            # Set read operation
            op.read.key = key  # This automatically creates the ReadOperation
            return op
        except Exception as e:
            raise ValueError(f"Invalid read operation: {op_str}") from e

    def _parse_write(self, op_str: str) -> replication_pb2.Operation:
        """Parse WRITE operation into protobuf Operation."""
        try:
            print("\nDebug _parse_write:")
            print(f"Input op_str: {op_str}")

            # Extract everything between w( and )
            start = op_str.index('(')
            end = op_str.rindex(')')
            content = op_str[start + 1:end]
            key_str, value_str = content.split(',')
            print(f"Parsed key_str: {key_str}, value_str: {value_str}")

            # Create operation and its write part
            op = replication_pb2.Operation()
            write_op = replication_pb2.WriteOperation()
            write_op.key = int(key_str.strip())
            write_op.value = int(value_str.strip())

            # Set the write operation
            op.write.CopyFrom(write_op)

            print(f"Final operation: {op}")
            return op
        except Exception as e:
            print(f"\nError in _parse_write:")
            print(f"Exception type: {type(e)}")
            print(f"Exception message: {str(e)}")
            raise ValueError(f"Invalid write operation: {op_str}") from e

    def parse(self, tx_str: str) -> replication_pb2.Transaction:
        """Parse a complete transaction string into a protobuf Transaction."""
        print(f"\nParsing transaction: {tx_str}")
        # Create transaction message
        tx = replication_pb2.Transaction()

        # First validate basic structure
        if not tx_str.startswith('b') or not tx_str.endswith('c'):
            raise ValueError("Transaction must start with BEGIN and end with COMMIT")

        # Split the transaction string preserving parentheses content
        parts = []
        current_part = ""
        in_parentheses = False

        for char in tx_str:
            if char == '(' and not in_parentheses:
                in_parentheses = True
                current_part += char
            elif char == ')' and in_parentheses:
                in_parentheses = False
                current_part += char
            elif char == ',' and not in_parentheses:
                if current_part:
                    parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char

        if current_part:
            parts.append(current_part.strip())

        # Parse BEGIN operation and set transaction type
        begin_op = parts[0]
        target_layer = self._parse_begin(begin_op)

        # Check for write operations
        has_write = any(p.startswith('w(') for p in parts)

        if has_write and target_layer != 0:
            raise ValueError("Write transactions must target core layer (use 'b' without layer number)")

        # Set transaction type and target layer
        tx.type = (replication_pb2.Transaction.UPDATE if has_write
                  else replication_pb2.Transaction.READ_ONLY)
        tx.target_layer = target_layer

        # Parse operations (skip BEGIN and COMMIT)
        for op_str in parts[1:-1]:
            op_str = op_str.strip()
            if op_str.startswith('r('):
                tx.operations.append(self._parse_read(op_str))
            elif op_str.startswith('w('):
                tx.operations.append(self._parse_write(op_str))
            else:
                raise ValueError(f"Invalid operation: {op_str}")

        return tx