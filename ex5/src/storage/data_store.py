"""Data store implementation for version management."""
from dataclasses import dataclass
from typing import Dict, Optional, List
import time
from pathlib import Path
import json

@dataclass
class DataItem:
    """Represents a versioned data item."""
    key: int
    value: int
    version: int
    timestamp: float

class DataStore:
    """Stores versioned data items and maintains a version log."""

    def __init__(self, node_id: str, log_dir: str):
        """Initialize data store.

        Args:
            node_id: Identifier for this node
            log_dir: Directory for storing version logs
        """
        self._data: Dict[int, DataItem] = {}
        self._log_file = Path(log_dir) / f"{node_id}_version_log.jsonl"
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def get(self, key: int) -> Optional[DataItem]:
        """Get data item by key.

        Args:
            key: Key of the data item

        Returns:
            DataItem if found, None otherwise
        """
        return self._data.get(key)

    def get_all(self) -> List[DataItem]:
        """Get all items in the store.

        Returns:
            List of all DataItems in the store
        """
        return list(self._data.values())

    async def update(self, key: int, value: int, version: int) -> DataItem:
        """Update or create a data item.

        Args:
            key: Key of the data item
            value: Value to store
            version: Version number of the update

        Returns:
            Updated DataItem
        """
        item = DataItem(
            key=key,
            value=value,
            version=version,
            timestamp=time.time()
        )
        self._data[key] = item

        with self._log_file.open('a') as f:
            json.dump({
                'key': item.key,
                'value': item.value,
                'version': item.version,
                'timestamp': item.timestamp
            }, f)
            f.write('\n')

        return item

