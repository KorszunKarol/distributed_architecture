"""Tests for the FirstLayerNode class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.node.first_layer_node import FirstLayerNode
from src.proto import replication_pb2
from src.replication.passive_replication import PassiveReplication

@pytest.fixture
def mock_store():
    """Create a mock data store."""
    store = Mock()
    store.get = AsyncMock()
    store.update = AsyncMock()
    store.get_all = AsyncMock()
    store.close = AsyncMock()
    return store

@pytest.fixture(scope="function")
async def first_layer_node(temp_log_dir):
    """Create a first layer node instance."""
    node = FirstLayerNode(
        node_id="first_layer_node",
        log_dir=str(temp_log_dir),
        port=50052,
        is_primary=True,
        backup_address="localhost:50053",
        second_layer_address="localhost:50054"
    )
    # Initialize mocks before starting
    node.store = Mock()
    node.store.get = AsyncMock()
    node.store.update = AsyncMock()
    node.store.get_all = AsyncMock()
    node.store.close = AsyncMock()
    
    # Keep the PassiveReplication instance but mock its methods
    node.replication.handle_update = AsyncMock()
    node.replication.start = AsyncMock()
    
    # Mock connection methods
    node._connect_to_backup = AsyncMock()
    node._connect_to_second_layer = AsyncMock()
    
    # Mock stubs
    node.backup_stub = Mock()
    node.next_layer_stub = Mock()
    
    try:
        yield node
    finally:
        await node.stop()

@pytest.mark.asyncio
class TestFirstLayerNode:
    """Test suite for FirstLayerNode class."""

    async def test_initialization(self, first_layer_node):
        """Test first layer node initialization."""
        # Test initial state before starting
        assert first_layer_node.node_id == "first_layer_node"
        assert first_layer_node.layer == 1  # First layer nodes are in layer 1
        assert first_layer_node.port == 50052
        assert isinstance(first_layer_node.replication, PassiveReplication)
        assert first_layer_node.is_primary
        assert first_layer_node.backup_address == "localhost:50053"
        assert first_layer_node.second_layer_address == "localhost:50054"
        assert not first_layer_node._closed
        assert not first_layer_node._ready.is_set()

        # Start the node
        await first_layer_node.start()

        # Test state after starting
        assert first_layer_node._ready.is_set()

    async def test_sync_updates(self, first_layer_node):
        """Test syncing updates from core layer."""
        # Mock store methods
        first_layer_node.store.update = AsyncMock()
        first_layer_node.replication.handle_update = AsyncMock(return_value=True)
        first_layer_node.is_primary = True
        first_layer_node.backup_stub = Mock()

        # Start the node
        await first_layer_node.start()

        # Create update group
        updates = [
            replication_pb2.DataItem(key=1, value=100, version=1),
            replication_pb2.DataItem(key=2, value=200, version=1)
        ]
        update_group = replication_pb2.UpdateGroup(
            source_node="core_node",
            layer=0,
            updates=updates
        )

        # Sync updates
        response = await first_layer_node.SyncUpdates(update_group, None)

        # Verify response
        assert response.success
        assert not response.message

        # Verify store updates
        assert first_layer_node.store.update.await_count == len(updates)
        assert first_layer_node.replication.handle_update.await_count == 1  # Called once with the entire update group

    async def test_sync_updates_store_error(self, first_layer_node):
        """Test error handling when store update fails."""
        # Mock store methods
        first_layer_node.store.update = AsyncMock(side_effect=Exception("Store error"))
        first_layer_node.is_primary = True
        first_layer_node.backup_stub = Mock()

        # Start the node
        await first_layer_node.start()

        # Create update group
        updates = [replication_pb2.DataItem(key=1, value=100, version=1)]
        update_group = replication_pb2.UpdateGroup(
            source_node="core_node",
            layer=0,
            updates=updates
        )

        # Sync updates and expect error response
        response = await first_layer_node.SyncUpdates(update_group, None)

        # Verify error response
        assert not response.success
        assert "Store error" in response.message

    async def test_sync_updates_replication_error(self, first_layer_node):
        """Test error handling when replication fails."""
        # Mock store success but replication failure
        first_layer_node.store.update = AsyncMock()
        first_layer_node.replication.handle_update = AsyncMock(return_value=False)
        first_layer_node.is_primary = True
        first_layer_node.backup_stub = Mock()

        # Start the node
        await first_layer_node.start()

        # Create update group
        updates = [replication_pb2.DataItem(key=1, value=100, version=1)]
        update_group = replication_pb2.UpdateGroup(
            source_node="core_node",
            layer=0,
            updates=updates
        )

        # Sync updates and expect error response
        response = await first_layer_node.SyncUpdates(update_group, None)

        # Verify error response
        assert not response.success
        assert "Replication failed" in response.message

    async def test_execute_read_only_transaction(self, first_layer_node):
        """Test executing a read-only transaction."""
        # Mock store data
        test_data = {
            30: replication_pb2.DataItem(key=30, value=300, version=1),
            49: replication_pb2.DataItem(key=49, value=490, version=1),
            69: replication_pb2.DataItem(key=69, value=690, version=1)
        }
        first_layer_node.store.get = AsyncMock(side_effect=lambda k: test_data.get(k))

        # Create a read-only transaction
        transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=30),
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=49),
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=69)
            ]
        )

        # Execute transaction
        result = await first_layer_node.ExecuteTransaction(transaction, None)

        # Verify results
        assert len(result.results) == 3
        assert result.results[0].value == 300
        assert result.results[1].value == 490
        assert result.results[2].value == 690

    async def test_execute_write_transaction_error(self, first_layer_node):
        """Test that write transactions are rejected."""
        # Mock store methods
        first_layer_node.store.update = Mock()
        first_layer_node.replication.handle_update = Mock()

        # Create a transaction with a write operation
        transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.WRITE, key=49, value=53)
            ]
        )

        # Execute transaction and expect error
        with pytest.raises(Exception, match="Write operations not allowed"):
            await first_layer_node.ExecuteTransaction(transaction, None)

        # Verify no store interactions
        first_layer_node.store.update.assert_not_called()
        first_layer_node.replication.handle_update.assert_not_called() 