import pytest
from datetime import datetime
import pathlib
import json
from src.storage.data_store import DataStore, DataItem

@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path

@pytest.fixture
def data_store(temp_dir):
    return DataStore("test_node", temp_dir)

def test_data_item_creation():
    item = DataItem(key=1, value=100, version=1, timestamp=datetime.now().timestamp())
    assert item.key == 1
    assert item.value == 100
    assert item.version == 1

def test_store_update(data_store):
    item = data_store.update(key=1, value=100, version=1)
    assert item.key == 1
    assert item.value == 100
    assert item.version == 1

def test_store_get(data_store):
    data_store.update(key=1, value=100, version=1)
    item = data_store.get(1)
    assert item is not None
    assert item.value == 100

def test_store_get_nonexistent(data_store):
    assert data_store.get(999) is None

def test_version_logging(data_store, temp_dir):
    data_store.update(key=1, value=100, version=1)

    log_file = temp_dir / "test_node_version_log.txt"
    assert log_file.exists()

    with open(log_file, 'r') as f:
        log_line = f.readline()
        log_entry = json.loads(log_line)
        assert log_entry['key'] == 1
        assert log_entry['value'] == 100
        assert log_entry['version'] == 1
        assert log_entry['node_id'] == "test_node"

def test_get_all_items(data_store):
    data_store.update(key=1, value=100, version=1)
    data_store.update(key=2, value=200, version=1)

    items = data_store.get_all_items()
    assert len(items) == 2
    assert any(item.key == 1 and item.value == 100 for item in items)
    assert any(item.key == 2 and item.value == 200 for item in items)