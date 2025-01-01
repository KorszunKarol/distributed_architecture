"""Tests for the CoreNode class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.node.core_node import CoreNode
from src.proto import replication_pb2
from src.replication.eager_replication import EagerReplication

@pytest.fixture
def mock_store():
    """Create a mock data store."""
    store = Mock()
    store.get = AsyncMock()
    store.update = AsyncMock()
    store.get_all = AsyncMock()
    store.close = AsyncMock()
    return store

@pytest.fixture
def core_node(temp_log_dir):
    """Create a core node instance."""
    node = CoreNode(
        node_id="core_node",
        log_dir=str(temp_log_dir),
        port=50051,
        peer_addresses=["localhost:50052", "localhost:50053"],
        is_first_node=True,
        first_layer_address="localhost:50054"
    )
    return node

@pytest.mark.asyncio
class TestCoreNode:
    """Test suite for CoreNode class."""

    async def test_initialization(self, core_node):
        """Test core node initialization."""
        assert core_node.node_id == "core_node"
        assert core_node.layer == 0  # Core layer is 0
        assert core_node.port == 50051
        assert isinstance(core_node.replication, EagerReplication)
        assert len(core_node.peer_addresses) == 2
        assert core_node.is_first_node
        assert core_node.first_layer_address == "localhost:50054"
        assert not core_node._closed
        assert not core_node._ready.is_set()

    async def test_execute_read_only_transaction(self, core_node):
        """Test executing a read-only transaction."""
        # Mock store data
        test_data = {
            30: replication_pb2.DataItem(key=30, value=300, version=1),
            49: replication_pb2.DataItem(key=49, value=490, version=1),
            69: replication_pb2.DataItem(key=69, value=690, version=1)
        }
        core_node.store.get = AsyncMock(side_effect=lambda k: test_data.get(k))

        # Create a read-only transaction
        transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=30),
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=49),
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=69)
            ]
        )

        # Execute transaction
        result = await core_node.ExecuteTransaction(transaction, None)

        # Verify results
        assert len(result.results) == 3
        assert result.results[0].value == 300
        assert result.results[1].value == 490
        assert result.results[2].value == 690

    async def test_execute_write_transaction(self, core_node):
        """Test executing a transaction with writes."""
        # Mock store methods
        test_data = {
            12: replication_pb2.DataItem(key=12, value=120, version=1),
            49: replication_pb2.DataItem(key=49, value=490, version=1),
            69: replication_pb2.DataItem(key=69, value=690, version=1)
        }
        core_node.store.get = AsyncMock(side_effect=lambda k: test_data.get(k))
        core_node.store.update = AsyncMock()
        core_node.replication.handle_update = AsyncMock(return_value=True)

        # Create a transaction with reads and writes
        transaction = replication_pb2.Transaction(
            type=replication_pb2.Transaction.UPDATE,
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=12),
                replication_pb2.Operation(type=replication_pb2.Operation.WRITE, key=49, value=53),
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=69)
            ]
        )

        # Execute transaction
        result = await core_node.ExecuteTransaction(transaction, None)

        # Verify results
        assert len(result.results) == 3
        assert result.results[0].value == 120  # First read
        assert result.results[1].value == 53   # Write result
        assert result.results[2].value == 690  # Second read

        # Verify store update was called
        core_node.store.update.assert_called_once()
        core_node.replication.handle_update.assert_called_once()

    async def test_execute_transaction_store_error(self, core_node):
        """Test error handling when store operations fail."""
        # Make store.get raise an exception
        core_node.store.get = AsyncMock(side_effect=Exception("Store error"))

        # Create a simple read transaction
        transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=30)
            ]
        )

        # Execute transaction and expect error
        with pytest.raises(Exception, match="Store error"):
            await core_node.ExecuteTransaction(transaction, None)

    async def test_execute_transaction_replication_error(self, core_node):
        """Test error handling when replication fails."""
        # Mock store methods
        test_data = {49: replication_pb2.DataItem(key=49, value=490, version=1)}
        core_node.store.get = AsyncMock(side_effect=lambda k: test_data.get(k))
        core_node.store.update = AsyncMock()
        
        # Make replication fail
        core_node.replication.handle_update = AsyncMock(return_value=False)

        # Create a write transaction
        transaction = replication_pb2.Transaction(
            type=replication_pb2.Transaction.UPDATE,
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.WRITE, key=49, value=53)
            ]
        )

        # Execute transaction and expect error
        with pytest.raises(Exception, match="Replication failed"):
            await core_node.ExecuteTransaction(transaction, None)

        # Verify store update was not committed
        core_node.store.update.assert_not_called() 