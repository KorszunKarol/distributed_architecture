"""Tests for the BaseReplication class."""
import pytest
from unittest.mock import Mock
from src.replication.base_replication import BaseReplication
from src.proto import replication_pb2

# Test implementation of BaseReplication
def create_test_replication():
    """Create a test replication instance."""
    class TestReplication(BaseReplication):
        def __init__(self):
            super().__init__(propagation_type='test', consistency_type='test')
            self.handle_update_called = False
            self.sync_called = False
            
        async def handle_update(self, data_item: replication_pb2.DataItem) -> bool:
            self.handle_update_called = True
            return True
            
        async def sync(self) -> None:
            self.sync_called = True
            
    return TestReplication()

@pytest.fixture
def replication():
    """Create a test replication instance."""
    return create_test_replication()

class TestBaseReplication:
    """Test suite for BaseReplication class."""

    def test_initialization(self, replication):
        """Test initialization of replication strategy."""
        assert replication.propagation_type == 'test'
        assert replication.consistency_type == 'test'
        assert replication.node is None
        assert not replication._running

    def test_set_node(self, replication):
        """Test setting node reference."""
        mock_node = Mock()
        replication.set_node(mock_node)
        assert replication.node == mock_node

    @pytest.mark.asyncio
    async def test_start_stop(self, replication):
        """Test starting and stopping replication."""
        assert not replication._running
        
        await replication.start()
        assert replication._running
        
        await replication.stop()
        assert not replication._running

    @pytest.mark.asyncio
    async def test_handle_update_implementation(self, replication):
        """Test that handle_update is called."""
        data_item = replication_pb2.DataItem(
            key=1,
            value=100,
            version=1
        )
        
        assert not replication.handle_update_called
        result = await replication.handle_update(data_item)
        assert result
        assert replication.handle_update_called

    @pytest.mark.asyncio
    async def test_sync_implementation(self, replication):
        """Test that sync is called."""
        assert not replication.sync_called
        await replication.sync()
        assert replication.sync_called

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""
        class IncompleteReplication(BaseReplication):
            def __init__(self):
                super().__init__('test', 'test')

        with pytest.raises(TypeError):
            IncompleteReplication() 