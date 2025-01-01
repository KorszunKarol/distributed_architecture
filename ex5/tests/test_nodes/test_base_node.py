"""Tests for the BaseNode class."""
import pytest
import grpc
from unittest.mock import Mock, AsyncMock, patch
from src.node.base_node import BaseNode
from src.proto import replication_pb2
from src.replication.base_replication import BaseReplication

def create_test_replication():
    """Create a test replication instance."""
    class TestReplication(BaseReplication):
        def __init__(self):
            super().__init__(propagation_type='test', consistency_type='test')
            
        async def handle_update(self, data_item: replication_pb2.DataItem) -> bool:
            return True
            
        async def sync(self) -> None:
            pass
            
    return TestReplication()

@pytest.fixture
def mock_store(temp_log_dir):
    """Create a mock data store."""
    store = Mock()
    store.get = AsyncMock()
    store.update = AsyncMock()
    store.get_all = AsyncMock()
    store.close = AsyncMock()
    return store

@pytest.fixture
def base_node(temp_log_dir):
    """Create a base node instance."""
    node = BaseNode(
        node_id="test_node",
        layer=0,
        log_dir=str(temp_log_dir),
        port=50051,
        replication_strategy=create_test_replication()
    )
    return node

@pytest.mark.asyncio
class TestBaseNode:
    """Test suite for BaseNode class."""

    async def test_initialization(self, base_node):
        """Test node initialization."""
        assert base_node.node_id == "test_node"
        assert base_node.layer == 0
        assert base_node.port == 50051
        assert base_node.replication is not None
        assert base_node.server is None
        assert not base_node._closed
        assert not base_node._ready.is_set()

    async def test_start_stop(self, base_node):
        """Test starting and stopping the node."""
        # Start the node
        await base_node.start()
        assert base_node.server is not None
        assert base_node._ready.is_set()

        # Stop the node
        await base_node.stop()
        assert not base_node._ready.is_set()
        assert base_node._closed

    async def test_wait_for_ready(self, base_node):
        """Test waiting for node to be ready."""
        # Node not ready yet
        ready = await base_node.wait_for_ready(timeout=0.1)
        assert not ready

        # Start node and wait
        await base_node.start()
        ready = await base_node.wait_for_ready(timeout=0.1)
        assert ready

        # Clean up
        await base_node.stop()

    async def test_get_node_status(self, base_node):
        """Test getting node status."""
        # Mock store data
        test_data = [
            replication_pb2.DataItem(key=1, value=100, version=1),
            replication_pb2.DataItem(key=2, value=200, version=2)
        ]
        base_node.store.get_all = AsyncMock(return_value=test_data)

        # Get status
        status = await base_node.GetNodeStatus(replication_pb2.Empty(), None)
        
        assert status.node_id == base_node.node_id
        assert status.layer == base_node.layer
        assert len(status.current_data) == len(test_data)
        for i, item in enumerate(status.current_data):
            assert item.key == test_data[i].key
            assert item.value == test_data[i].value
            assert item.version == test_data[i].version

    async def test_get_node_status_error(self, base_node):
        """Test error handling in get node status."""
        # Make store.get_all raise an exception
        base_node.store.get_all = AsyncMock(side_effect=Exception("Store error"))

        with pytest.raises(Exception, match="Store error"):
            await base_node.GetNodeStatus(replication_pb2.Empty(), None)

    async def test_server_startup_error(self, base_node):
        """Test handling server startup errors."""
        # Mock server.start to raise an error
        with patch('grpc.aio.server') as mock_server:
            mock_server.return_value.start = AsyncMock(side_effect=Exception("Server error"))
            with pytest.raises(Exception, match="Server error"):
                await base_node.start()

        assert not base_node._ready.is_set()

    async def test_cleanup_on_stop(self, base_node):
        """Test proper cleanup when stopping the node."""
        # Create a mock store with close method
        mock_store = Mock()
        mock_store.close = AsyncMock()
        base_node.store = mock_store

        # Start and stop the node
        await base_node.start()
        await base_node.stop()

        # Verify store was closed
        assert mock_store.close.await_count == 1

        # Verify server was stopped
        assert not base_node._ready.is_set()
        assert base_node._closed
