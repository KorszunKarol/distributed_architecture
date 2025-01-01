"""Tests for the PassiveReplication class."""
import pytest
from unittest.mock import Mock, AsyncMock
import grpc
from src.replication.passive_replication import PassiveReplication
from src.proto import replication_pb2

@pytest.fixture
def mock_node():
    """Create a mock node for testing."""
    node = Mock()
    node.node_id = "test_node"
    node.layer = 1
    node.store = Mock()
    node.store.update = AsyncMock()
    node.store.get_all = AsyncMock()
    node.backup_stub = None
    node.is_primary = True
    return node

@pytest.fixture
def passive_replication(mock_node):
    """Create a passive replication instance with a mock node."""
    replication = PassiveReplication()
    replication.set_node(mock_node)
    return replication

@pytest.fixture
def data_items():
    """Create test data items."""
    return [
        replication_pb2.DataItem(key=1, value=100, version=1),
        replication_pb2.DataItem(key=2, value=200, version=2)
    ]

class TestPassiveReplication:
    """Test suite for PassiveReplication class."""

    def test_initialization(self, passive_replication):
        """Test initialization of passive replication."""
        assert passive_replication.propagation_type == 'passive'
        assert passive_replication.consistency_type == 'lazy'

    @pytest.mark.asyncio
    async def test_sync_primary_with_backup(self, passive_replication, data_items):
        """Test sync operation when primary with backup."""
        # Setup mock backup stub
        backup_stub = AsyncMock()
        backup_stub.SyncUpdates = AsyncMock(
            return_value=replication_pb2.AckResponse(success=True)
        )
        passive_replication.node.backup_stub = backup_stub
        passive_replication.node.store.get_all.return_value = data_items

        await passive_replication.sync()

        # Verify backup was called with correct data
        backup_stub.SyncUpdates.assert_awaited_once()
        notification = backup_stub.SyncUpdates.call_args[0][0]
        assert len(notification.updates) == len(data_items)
        assert notification.source_node == passive_replication.node.node_id
        assert notification.layer == passive_replication.node.layer
        assert notification.update_count == len(data_items)

    @pytest.mark.asyncio
    async def test_sync_backup_no_action(self, passive_replication):
        """Test sync operation when backup node."""
        passive_replication.node.is_primary = False
        await passive_replication.sync()
        passive_replication.node.store.get_all.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_update_primary_with_backup(self, passive_replication, data_items):
        """Test handling update as primary with backup."""
        # Setup mock backup stub
        backup_stub = AsyncMock()
        backup_stub.SyncUpdates = AsyncMock(
            return_value=replication_pb2.AckResponse(success=True)
        )
        passive_replication.node.backup_stub = backup_stub

        result = await passive_replication.handle_update(data_items)
        assert result is True

        # Verify local updates
        assert passive_replication.node.store.update.await_count == len(data_items)
        for item in data_items:
            passive_replication.node.store.update.assert_any_await(
                key=item.key,
                value=item.value,
                version=item.version
            )

        # Verify backup propagation
        backup_stub.SyncUpdates.assert_awaited_once()
        notification = backup_stub.SyncUpdates.call_args[0][0]
        assert len(notification.updates) == len(data_items)
        assert notification.source_node == passive_replication.node.node_id
        assert notification.layer == passive_replication.node.layer

    @pytest.mark.asyncio
    async def test_handle_update_backup_no_action(self, passive_replication, data_items):
        """Test handling update as backup node."""
        passive_replication.node.is_primary = False
        result = await passive_replication.handle_update(data_items)
        assert result is False
        passive_replication.node.store.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_handle_update_primary_no_backup(self, passive_replication, data_items):
        """Test handling update as primary without backup."""
        passive_replication.node.backup_stub = None

        result = await passive_replication.handle_update(data_items)
        assert result is True

        # Verify only local updates
        assert passive_replication.node.store.update.await_count == len(data_items)
        for item in data_items:
            passive_replication.node.store.update.assert_any_await(
                key=item.key,
                value=item.value,
                version=item.version
            )

    @pytest.mark.asyncio
    async def test_handle_update_backup_failure(self, passive_replication, data_items):
        """Test handling update when backup sync fails."""
        # Setup mock backup stub that fails
        backup_stub = AsyncMock()
        backup_stub.SyncUpdates = AsyncMock(
            side_effect=grpc.aio.AioRpcError(
                code=grpc.StatusCode.UNAVAILABLE,
                initial_metadata=None,
                trailing_metadata=None,
                details="Connection failed"
            )
        )
        passive_replication.node.backup_stub = backup_stub

        result = await passive_replication.handle_update(data_items)
        assert result is False  # Should fail due to backup failure

        # Verify local updates were still attempted
        assert passive_replication.node.store.update.await_count == len(data_items)
        for item in data_items:
            passive_replication.node.store.update.assert_any_await(
                key=item.key,
                value=item.value,
                version=item.version
            ) 