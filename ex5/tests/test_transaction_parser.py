"""Tests for the transaction parser."""
import pytest
from src.transaction.parser import TransactionParser
from src.proto import replication_pb2

@pytest.fixture
def parser():
    """Create a parser instance for testing."""
    return TransactionParser()

class TestTransactionParser:
    """Test suite for TransactionParser."""

    def test_read_only_transaction(self, parser):
        """Test parsing a read-only transaction."""
        result = parser.parse("b<0>, r(1), r(2), c")
        assert result.type == replication_pb2.Transaction.READ_ONLY
        assert result.target_layer == 0
        assert len(result.operations) == 2
        assert result.operations[0].read.key == 1
        assert result.operations[1].read.key == 2

    def test_write_transaction(self, parser):
        """Test parsing a write transaction."""
        result = parser.parse("b, w(1,100), w(2,200), c")
        assert result.type == replication_pb2.Transaction.UPDATE
        assert result.target_layer == 0
        assert len(result.operations) == 2
        assert result.operations[0].write.key == 1
        assert result.operations[0].write.value == 100
        assert result.operations[1].write.key == 2
        assert result.operations[1].write.value == 200

    def test_mixed_transaction(self, parser):
        """Test parsing a mixed read-write transaction."""
        result = parser.parse("b, r(12), w(49,53), r(69), c")
        assert result.type == replication_pb2.Transaction.UPDATE
        assert result.target_layer == 0
        assert len(result.operations) == 3
        assert result.operations[0].read.key == 12
        assert result.operations[1].write.key == 49
        assert result.operations[1].write.value == 53
        assert result.operations[2].read.key == 69

    def test_write_with_layer_fails(self, parser):
        """Test that write transactions with layer specification fail."""
        with pytest.raises(ValueError, match="Write transactions must target core layer"):
            parser.parse("b<1>, w(1,100), c")

    def test_invalid_transaction_format(self, parser):
        """Test invalid transaction formats."""
        invalid_cases = [
            ("r(1), r(2), c", "Transaction must start with BEGIN"),  # Missing BEGIN
            ("b, r(1)", "Transaction must start with BEGIN"),        # Missing COMMIT
            ("b, r(x), c", "Invalid read operation"),               # Invalid read key
            ("b, w(1:100), c", "Invalid write operation"),         # Wrong write format
            ("b, w(1,), c", "Invalid write operation"),            # Missing write value
            ("b, w(,100), c", "Invalid write operation"),          # Missing write key
        ]

        for tx_str, expected_error in invalid_cases:
            with pytest.raises(ValueError, match=expected_error):
                parser.parse(tx_str)

    def test_layer_specification(self, parser):
        """Test layer specification in transactions."""
        test_cases = [
            ("b<2>, r(1), r(2), c", 2),
            ("b, r(1), r(2), c", 0),
            ("b<0>, r(1), r(2), c", 0),
        ]

        for tx_str, expected_layer in test_cases:
            result = parser.parse(tx_str)
            assert result.target_layer == expected_layer
