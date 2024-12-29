from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import json
import pathlib
import asyncio


@dataclass
class DataItem:
    """A single data item in the store with versioning information."""
    key: int
    value: int
    version: int
    timestamp: float

    def to_dict(self) -> dict:
        """Convert the data item to a dictionary format."""
        return {
            'key': self.key,
            'value': self.value,
            'version': self.version,
            'timestamp': self.timestamp
        }


class DataStore:
    """Storage manager for versioned data items with logging capabilities."""

    def __init__(self, node_id: str, log_dir: pathlib.Path):
        """Initialize a new data store.

        Args:
            node_id: Identifier for the node owning this store
            log_dir: Directory path for storing version logs
        """
        self._data: Dict[int, DataItem] = {}
        self._log_file = log_dir / f"{node_id}_version_log.txt"
        self.node_id = node_id
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def get(self, key: int) -> Optional[DataItem]:
        """Retrieve a data item by its key.

        Args:
            key: The key of the data item to retrieve

        Returns:
            The DataItem if found, None otherwise
        """
        return self._data.get(key)

    async def update(self, key: int, value: int, version: int) -> DataItem:
        """Update or create a data item with versioning.

        Args:
            key: The key of the data item
            value: The new value to set
            version: The version number of the update

        Returns:
            The updated DataItem
        """
        async with self._lock:
            item = DataItem(
                key=key,
                value=value,
                version=version,
                timestamp=datetime.now().timestamp()
            )
            self._data[key] = item
            await self._log_update(item)
            return item

    async def _log_update(self, item: DataItem):
        """Log an update to the version history file.

        Args:
            item: The DataItem that was updated
        """
        log_entry = {
            'timestamp': datetime.fromtimestamp(item.timestamp).isoformat(),
            'node_id': self.node_id,
            **item.to_dict()
        }
        async with asyncio.Lock():
            with open(self._log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

    def get_all_items(self) -> list[DataItem]:
        """Get all data items currently in the store.

        Returns:
            List of all stored DataItems
        """
        return list(self._data.values())