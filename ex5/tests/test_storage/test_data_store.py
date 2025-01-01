"""Tests for the DataStore class."""
import pytest
import os
import asyncio
from unittest.mock import Mock, AsyncMock
from src.storage.data_store import DataStore
from src.proto import replication_pb2

@pytest.fixture
def data_store(temp_log_dir):
    """Create a data store instance."""
    return DataStore("test_node", temp_log_dir)

@pytest.mark.asyncio
class TestDataStore:
    """Test suite for DataStore class."""

    async def test_update_and_get(self, data_store):
        """Test updating and retrieving data."""
        # Update data
        await data_store.update(key=1, value=100, version=1)
        
        # Get data
        item = await data_store.get(1)
        assert item.key == 1
        assert item.value == 100
        assert item.version == 1

    async def test_get_nonexistent(self, data_store):
        """Test getting nonexistent data."""
        item = await data_store.get(1)
        assert item is None

    async def test_get_all(self, data_store):
        """Test getting all data."""
        # Add some data
        await data_store.update(key=1, value=100, version=1)
        await data_store.update(key=2, value=200, version=2)
        
        # Get all data
        items = await data_store.get_all()
        assert len(items) == 2
        assert items[0].key == 1
        assert items[0].value == 100
        assert items[1].key == 2
        assert items[1].value == 200

    async def test_version_increment(self, data_store):
        """Test version incrementing."""
        version1 = data_store.get_next_version()
        version2 = data_store.get_next_version()
        assert version2 > version1

    async def test_update_history(self, data_store):
        """Test update history tracking."""
        # Add some updates
        await data_store.update(key=1, value=100, version=1)
        await data_store.update(key=1, value=200, version=2)
        
        # Get recent updates
        updates = data_store.get_recent_updates(2)
        assert len(updates) == 2
        assert updates[0].key == 1
        assert updates[0].value == 100
        assert updates[1].value == 200

    async def test_log_file_creation(self, data_store, temp_log_dir):
        """Test that log files are created and written to."""
        await data_store.update(key=1, value=100, version=1)
    
        # Check version history file
        version_file = os.path.join(temp_log_dir, "test_node_version_history.jsonl")
        assert os.path.exists(version_file)
        
        # Check data file
        data_file = os.path.join(temp_log_dir, "test_node_data.jsonl")
        assert os.path.exists(data_file)

    async def test_concurrent_updates(self, data_store):
        """Test concurrent updates."""
        # Simulate concurrent updates
        await asyncio.gather(
            data_store.update(key=1, value=100, version=1),
            data_store.update(key=2, value=200, version=2)
        )
        
        # Verify both updates succeeded
        item1 = await data_store.get(1)
        item2 = await data_store.get(2)
        assert item1.value == 100
        assert item2.value == 200

    async def test_error_handling(self, data_store):
        """Test error handling."""
        # Test invalid version
        with pytest.raises(ValueError):
            await data_store.update(key=1, value=100, version=-1)
            
        # Test invalid key
        with pytest.raises(ValueError):
            await data_store.update(key=-1, value=100, version=1) 