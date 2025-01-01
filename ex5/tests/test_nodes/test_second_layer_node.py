"""Tests for the SecondLayerNode class."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.node.second_layer_node import SecondLayerNode
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
async def second_layer_node(temp_log_dir):
    """Create a second layer node instance."""
    node = SecondLayerNode(
        node_id="second_layer_node",
        log_dir=str(temp_log_dir),
        port=50053,
        is_primary=True,
        backup_addresses=["localhost:50054"]
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
    
    # Mock stubs
    node.backup_stub = Mock()
    
    try:
        yield node
    finally:
        await node.stop()

@pytest.mark.asyncio
class TestSecondLayerNode:
    """Test suite for SecondLayerNode class."""

    async def test_initialization(self, second_layer_node):
        """Test second layer node initialization."""
        # Test initial state before starting
        assert second_layer_node.node_id == "second_layer_node"
        assert second_layer_node.layer == 2  # Second layer nodes are in layer 2
        assert second_layer_node.port == 50053
        assert isinstance(second_layer_node.replication, PassiveReplication)
        assert second_layer_node.is_primary
        assert second_layer_node.backup_addresses == ["localhost:50054"]
        assert not second_layer_node._closed
        assert not second_layer_node._ready.is_set()

        # Start the node
        await second_layer_node.start()

        # Test state after starting
        assert second_layer_node._ready.is_set()

    async def test_sync_updates(self, second_layer_node):
        """Test syncing updates from first layer."""
        # Mock store methods
        second_layer_node.store.update = AsyncMock()
        second_layer_node.replication.handle_update = AsyncMock(return_value=True)
        second_layer_node.is_primary = True
        second_layer_node.backup_stubs = {"localhost:50054": Mock()}

        # Start the node
        await second_layer_node.start()

        # Create update group
        updates = [
            replication_pb2.DataItem(key=1, value=100, version=1),
            replication_pb2.DataItem(key=2, value=200, version=1)
        ]
        update_group = replication_pb2.UpdateGroup(
            source_node="first_layer_node",
            layer=1,
            updates=updates
        )

        # Sync updates
        response = await second_layer_node.SyncUpdates(update_group, None)

        # Verify response
        assert response.success
        assert not response.message

        # Verify store updates
        assert second_layer_node.store.update.await_count == len(updates)
        assert second_layer_node.replication.handle_update.await_count == 1  # Called once with the entire update group

    async def test_sync_updates_store_error(self, second_layer_node):
        """Test error handling when store update fails."""
        # Start the node
        await second_layer_node.start()

        # Make store.update raise an exception
        second_layer_node.store.update = AsyncMock(side_effect=Exception("Store error"))
        second_layer_node.is_primary = True
        second_layer_node.backup_stub = Mock()

        # Create update group
        updates = [replication_pb2.DataItem(key=1, value=100, version=1)]
        update_group = replication_pb2.UpdateGroup(
            source_node="first_layer_node",
            layer=1,
            updates=updates
        )

        # Sync updates and expect error response
        response = await second_layer_node.SyncUpdates(update_group, None)

        # Verify error response
        assert not response.success
        assert "Store error" in response.message

    async def test_sync_updates_replication_error(self, second_layer_node):
        """Test error handling when replication fails."""
        # Mock store success but replication failure
        second_layer_node.store.update = AsyncMock()
        second_layer_node.replication.handle_update = AsyncMock(return_value=False)
        second_layer_node.is_primary = True
        second_layer_node.backup_stubs = {"localhost:50054": Mock()}

        # Start the node
        await second_layer_node.start()

        # Create update group
        updates = [replication_pb2.DataItem(key=1, value=100, version=1)]
        update_group = replication_pb2.UpdateGroup(
            source_node="first_layer_node",
            layer=1,
            updates=updates
        )

        # Sync updates and expect error response
        response = await second_layer_node.SyncUpdates(update_group, None)

        # Verify error response
        assert not response.success
        assert "Replication failed" in response.message

    async def test_execute_read_only_transaction(self, second_layer_node):
        """Test executing a read-only transaction."""
        # Start the node
        await second_layer_node.start()

        # Mock store data
        test_data = {
            30: replication_pb2.DataItem(key=30, value=300, version=1),
            49: replication_pb2.DataItem(key=49, value=490, version=1),
            69: replication_pb2.DataItem(key=69, value=690, version=1)
        }
        second_layer_node.store.get = AsyncMock(side_effect=lambda k: test_data.get(k))

        # Create a read-only transaction
        transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=30),
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=49),
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=69)
            ]
        )

        # Execute transaction
        result = await second_layer_node.ExecuteTransaction(transaction, None)

        # Verify results
        assert len(result.results) == 3
        assert result.results[0].value == 300
        assert result.results[1].value == 490
        assert result.results[2].value == 690

    async def test_execute_write_transaction_error(self, second_layer_node):
        """Test that write transactions are rejected."""
        # Start the node
        await second_layer_node.start()

        # Mock store methods
        second_layer_node.store.update = Mock()
        second_layer_node.replication.handle_update = Mock()

        # Create a transaction with a write operation
        transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.WRITE, key=49, value=53)
            ]
        )

        # Execute transaction and expect error
        with pytest.raises(Exception, match="Write operations not allowed"):
            await second_layer_node.ExecuteTransaction(transaction, None)

        # Verify no store interactions
        second_layer_node.store.update.assert_not_called()
        second_layer_node.replication.handle_update.assert_not_called() 