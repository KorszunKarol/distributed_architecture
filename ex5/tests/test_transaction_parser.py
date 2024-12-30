"""Tests for the transaction parser."""
import pytest
from src.transaction.parser import TransactionParser, Operation, OperationType

@pytest.fixture
def parser():
    return TransactionParser()

class TestTransactionParser:
    def test_read_only_transaction(self, parser):
        result = parser.parse("b0,r(1),r(2),c")
        assert len(result) == 4
        assert result[0].type == OperationType.BEGIN
        assert result[0].layer == 0
        assert result[1].type == OperationType.READ
        assert result[1].key == 1
        assert result[2].type == OperationType.READ
        assert result[2].key == 2
        assert result[3].type == OperationType.COMMIT

    def test_write_transaction(self, parser):
        result = parser.parse("b,w(1,100),w(2,200),c")
        assert len(result) == 4
        assert result[0].type == OperationType.BEGIN
        assert result[0].layer == 0
        assert result[1].type == OperationType.WRITE
        assert result[1].key == 1
        assert result[1].value == 100
        assert result[2].type == OperationType.WRITE
        assert result[2].key == 2
        assert result[2].value == 200

    def test_mixed_transaction(self, parser):
        result = parser.parse("b,r(12),w(49,53),r(69),c")
        assert len(result) == 5
        assert result[1].type == OperationType.READ
        assert result[1].key == 12
        assert result[2].type == OperationType.WRITE
        assert result[2].key == 49
        assert result[2].value == 53

    def test_write_with_layer_fails(self, parser):
        with pytest.raises(ValueError, match="Write transactions must target core layer"):
            parser.parse("b1,w(1,100),c")

    def test_invalid_transaction_format(self, parser):
        with pytest.raises(ValueError):
            parser.parse("r(1),r(2)")  # Missing BEGIN/COMMIT
        with pytest.raises(ValueError):
            parser.parse("b0,r(1)")    # Missing COMMIT
        with pytest.raises(ValueError):
            parser.parse("b0,r(x),c")  # Invalid read key

    def test_write_operation_format(self, parser):
        with pytest.raises(ValueError):
            parser.parse("b,w(1:100),c")  # Wrong separator
        with pytest.raises(ValueError):
            parser.parse("b,w(1,),c")     # Missing value
        with pytest.raises(ValueError):
            parser.parse("b,w(,100),c")   # Missing key

    def test_layer_propagation(self, parser):
        transactions = [
            "b2,r(1),r(2),c",
            "b,w(1,100),w(2,200),c",
            "b,r(12),w(49,53),r(69),c",
            "b,w(1,100),w(2,200),c",
            "b,r(12),w(49,53),r(69),c",
        ]
        for tx in transactions:
            result = parser.parse(tx)
            layer = result[0].layer
            assert all(op.layer == layer for op in result)
