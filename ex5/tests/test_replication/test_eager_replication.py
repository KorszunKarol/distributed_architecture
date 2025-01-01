"""Tests for the EagerReplication class."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import grpc
from src.replication.eager_replication import EagerReplication
from src.proto import replication_pb2

@pytest.fixture
def mock_node():
    """Create a mock node for testing."""
    node = Mock()
    node.node_id = "test_node"
    node.store = Mock()
    node.store.update = AsyncMock()
    node.store.get = Mock()
    node.peer_stubs = {}
    return node

@pytest.fixture
def eager_replication(mock_node):
    """Create an eager replication instance with a mock node."""
    replication = EagerReplication()
    replication.set_node(mock_node)
    return replication

@pytest.fixture
def data_item():
    """Create a test data item."""
    return replication_pb2.DataItem(
        key=1,
        value=100,
        version=1,
        timestamp=int(asyncio.get_event_loop().time())
    )

class TestEagerReplication:
    """Test suite for EagerReplication class."""

    def test_initialization(self, eager_replication):
        """Test initialization of eager replication."""
        assert eager_replication.propagation_type == 'active'
        assert eager_replication.consistency_type == 'eager'
        assert eager_replication._propagation_timeout == 5.0

    @pytest.mark.asyncio
    async def test_sync_no_action(self, eager_replication):
        """Test that sync does nothing for eager replication."""
        await eager_replication.sync()
        # No assertions needed as sync is a no-op for eager replication

    @pytest.mark.asyncio
    async def test_handle_update_no_peers(self, eager_replication, data_item):
        """Test handling update with no peer nodes."""
        result = await eager_replication.handle_update(data_item)
        assert result is True
        eager_replication.node.store.update.assert_awaited_once_with(
            key=data_item.key,
            value=data_item.value,
            version=data_item.version
        )

    @pytest.mark.asyncio
    async def test_handle_update_with_peers(self, eager_replication, data_item):
        """Test handling update with peer nodes."""
        # Create mock peer stubs
        peer1 = AsyncMock()
        peer1.PropagateUpdate = AsyncMock(return_value=replication_pb2.AckResponse(success=True))
        peer2 = AsyncMock()
        peer2.PropagateUpdate = AsyncMock(return_value=replication_pb2.AckResponse(success=True))
        
        eager_replication.node.peer_stubs = {
            "peer1": peer1,
            "peer2": peer2
        }

        result = await eager_replication.handle_update(data_item)
        assert result is True

        # Verify local update
        eager_replication.node.store.update.assert_awaited_once_with(
            key=data_item.key,
            value=data_item.value,
            version=data_item.version
        )

        # Verify propagation to peers
        expected_notification = replication_pb2.UpdateNotification(
            data=data_item,
            source_node=eager_replication.node.node_id
        )

        for peer in [peer1, peer2]:
            peer.PropagateUpdate.assert_awaited_once()
            actual_notification = peer.PropagateUpdate.call_args[0][0]
            assert actual_notification.data.key == expected_notification.data.key
            assert actual_notification.data.value == expected_notification.data.value
            assert actual_notification.source_node == expected_notification.source_node

    @pytest.mark.asyncio
    async def test_handle_update_peer_failure(self, eager_replication, data_item):
        """Test handling update when a peer fails."""
        # Create mock peer stubs with one failing
        peer1 = AsyncMock()
        peer1.PropagateUpdate = AsyncMock(return_value=replication_pb2.AckResponse(success=True))
        peer2 = AsyncMock()
        peer2.PropagateUpdate = AsyncMock(
            side_effect=grpc.aio.AioRpcError(
                code=grpc.StatusCode.UNAVAILABLE,
                initial_metadata=None,
                trailing_metadata=None,
                details="Connection failed"
            )
        )
        
        eager_replication.node.peer_stubs = {
            "peer1": peer1,
            "peer2": peer2
        }

        result = await eager_replication.handle_update(data_item)
        assert result is False  # Should fail due to peer failure

        # Verify local update was still attempted
        eager_replication.node.store.update.assert_awaited_once_with(
            key=data_item.key,
            value=data_item.value,
            version=data_item.version
        )

    @pytest.mark.asyncio
    async def test_propagate_update(self, eager_replication, data_item):
        """Test handling propagated update from another node."""
        notification = replication_pb2.UpdateNotification(
            data=data_item,
            source_node="other_node"
        )

        response = await eager_replication.PropagateUpdate(notification, None)
        assert response.success is True

        # Verify local update
        eager_replication.node.store.update.assert_awaited_once_with(
            key=data_item.key,
            value=data_item.value,
            version=data_item.version
        )

    @pytest.mark.asyncio
    async def test_propagate_update_failure(self, eager_replication, data_item):
        """Test handling propagated update when local update fails."""
        notification = replication_pb2.UpdateNotification(
            data=data_item,
            source_node="other_node"
        )

        # Make local update fail
        eager_replication.node.store.update.side_effect = Exception("Update failed")

        response = await eager_replication.PropagateUpdate(notification, None)
        assert response.success is False
        assert "Update failed" in response.message 