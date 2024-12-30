"""Transaction parser module for handling transaction strings."""
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

class OperationType(Enum):
    """Enum representing different types of operations."""
    READ = "r"
    WRITE = "w"
    BEGIN = "b"
    COMMIT = "c"

@dataclass
class Operation:
    """Represents a single operation in a transaction."""
    type: OperationType
    key: Optional[int] = None
    value: Optional[int] = None
    layer: Optional[int] = None

class TransactionParser:
    """Class for parsing transaction strings into operations."""

    def _parse_begin(self, op_str: str, layer: int) -> Operation:
        """Parse BEGIN operation."""
        return Operation(type=OperationType.BEGIN, layer=layer)

    def _parse_read(self, op_str: str, layer: int) -> Operation:
        """Parse READ operation."""
        try:
            # Extract key between r( and )
            start = op_str.index('(')
            end = op_str.rindex(')')
            key = int(op_str[start + 1:end])
            return Operation(type=OperationType.READ, key=key, layer=layer)
        except Exception:
            raise ValueError(f"Invalid read operation: {op_str}")

    def _parse_write(self, op_str: str, layer: int) -> Operation:
        """Parse WRITE operation."""
        try:
            # Extract everything between w( and )
            start = op_str.index('(')
            end = op_str.rindex(')')  # Use rindex to find the last )
            content = op_str[start + 1:end]
            print(f"Content: {content}")

            # Split into key and value
            key_str, value_str = content.split(',')
            return Operation(
                type=OperationType.WRITE,
                key=int(key_str),
                value=int(value_str),
                layer=layer
            )
        except Exception:
            raise ValueError(f"Invalid write operation: {op_str}")

    def parse_operation(self, op_str: str, layer: int) -> Operation:
        """
        Parse a single operation string.

        Args:
            op_str: The operation string to parse
            layer: The layer number from the BEGIN operation
        """
        op_str = op_str.strip()

        if op_str.startswith('b'):
            return self._parse_begin(op_str, layer)

        if op_str == 'c':
            return Operation(type=OperationType.COMMIT, layer=layer)

        if op_str.startswith('r'):
            return self._parse_read(op_str, layer)

        if op_str.startswith('w'):
            return self._parse_write(op_str, layer)

        raise ValueError(f"Invalid operation format: {op_str}")

    def parse(self, tx_str: str) -> List[Operation]:
        """Parse a complete transaction string into a list of operations."""
        # First validate basic structure
        if not tx_str.startswith('b') or not tx_str.endswith('c'):
            raise ValueError("Transaction must start with BEGIN and end with COMMIT")

        # Check for write operations
        has_write = 'w(' in tx_str

        # Get the layer from the first character after 'b'
        layer = 0
        if tx_str[1].isdigit():
            if has_write:
                raise ValueError("Write transactions must target core layer (use 'b' without layer number)")
            layer = int(tx_str[1])
            tx_str = 'b' + tx_str[2:]  # Remove layer number from string
        elif has_write:
            layer = 0  # Force core layer for write transactions

        # Split the transaction string preserving parentheses content
        operations = []
        current_op = ""
        in_parentheses = False

        for char in tx_str:
            if char == '(' and not in_parentheses:
                in_parentheses = True
                current_op += char
            elif char == ')' and in_parentheses:
                in_parentheses = False
                current_op += char
            elif char == ',' and not in_parentheses:
                if current_op:
                    operations.append(current_op.strip())
                current_op = ""
            else:
                current_op += char

        if current_op:
            operations.append(current_op.strip())

        return [self.parse_operation(op, layer) for op in operations]


def main():
    parser = TransactionParser()
    test_cases = [
        "b0,r(1),r(2),c",                    # Basic read transaction
        "b1,w(1,100),w(2,200),c",            # Basic write transaction
        "b,r(12),w(49,53),r(69),c",          # Mixed transaction
        "b2,r(30),r(49),r(69),c",            # Multi-read transaction
        "b0,w(1,100),w(2,200),w(3,300),c",   # Multi-write transaction
        "b0,r(1,c",                          # Malformed read
        "b0,w(1:100),c",                     # Invalid write format
        "r(1),r(2),c",                       # Missing BEGIN
        "b0,r(1),r(2)"                       # Missing COMMIT
    ]

    for tx in test_cases:
        print(f"\nTesting transaction: {tx}")
        try:
            result = parser.parse(tx)
            print("Parsed operations:")
            for op in result:
                print(f"  {op}")
        except ValueError as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()