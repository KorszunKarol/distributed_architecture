"""Data store implementation for version management."""
from typing import Dict, Optional, List
import time
from pathlib import Path
import json
from src.proto import replication_pb2

class DataStore:
    """Stores versioned data items and maintains a version log."""

    def __init__(self, node_id: str, log_dir: str):
        self._data: Dict[int, replication_pb2.DataItem] = {}
        self._log_file = Path(log_dir) / f"{node_id}_version_log.jsonl"
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self.node_id = node_id
        self.current_version = 0

    def get(self, key: int) -> Optional[replication_pb2.DataItem]:
        return self._data.get(key)

    def get_all(self) -> List[replication_pb2.DataItem]:
        return list(self._data.values())

    async def update(self, key: int, value: int, version: int) -> replication_pb2.DataItem:
        item = replication_pb2.DataItem(
            key=key,
            value=value,
            version=version,
            timestamp=int(time.time())
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

    def get_next_version(self) -> int:
        self.current_version += 1
        return self.current_version

    def get_recent_updates(self, count: int) -> List[replication_pb2.DataItem]:
        return list(self._data.values())[-count:]

    async def close(self):
        pass
