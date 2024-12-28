from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import json
import pathlib


@dataclass
class DataItem:
    """Represents a single data item in the store.

    Attributes:
        key: The unique identifier for the data item.
        value: The current value of the data item.
        version: The version number of the data item.
        timestamp: The timestamp of the last update.
    """
    key: int
    value: int
    version: int
    timestamp: float

    def to_dict(self) -> dict:
        """Converts the data item to a dictionary representation."""
        return {
            'key': self.key,
            'value': self.value,
            'version': self.version,
            'timestamp': self.timestamp
        }


class DataStore:
    """Manages the storage and versioning of data items.

    Attributes:
        _data: Dictionary storing the current state of data items.
        _log_file: Path to the file where version history is logged.
        node_id: Identifier for the node owning this store.
    """

    def __init__(self, node_id: str, log_dir: pathlib.Path):
        self._data: Dict[int, DataItem] = {}
        self._log_file = log_dir / f"{node_id}_version_log.txt"
        self.node_id = node_id
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def get(self, key: int) -> Optional[DataItem]:
        """Retrieves a data item by its key.

        Args:
            key: The key of the data item to retrieve.

        Returns:
            The DataItem if found, None otherwise.
        """
        return self._data.get(key)

    def update(self, key: int, value: int, version: int) -> DataItem:
        """Updates or creates a data item.

        Args:
            key: The key of the data item.
            value: The new value to set.
            version: The version number of the update.

        Returns:
            The updated DataItem.
        """
        item = DataItem(
            key=key,
            value=value,
            version=version,
            timestamp=datetime.now().timestamp()
        )
        self._data[key] = item
        self._log_update(item)
        return item

    def _log_update(self, item: DataItem):
        """Logs an update to the version log file.

        Args:
            item: The DataItem that was updated.
        """
        log_entry = {
            'timestamp': datetime.fromtimestamp(item.timestamp).isoformat(),
            'node_id': self.node_id,
            **item.to_dict()
        }
        with open(self._log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def get_all_items(self) -> list[DataItem]:
        """Returns all data items in the store.

        Returns:
            List of all DataItems currently in the store.
        """
        return list(self._data.values())