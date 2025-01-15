"""Data store implementation for version management."""
from typing import Dict, Optional, List
import logging
import json
from pathlib import Path
import time
from collections import deque
from src.proto import replication_pb2

class DataStore:
    def __init__(self, node_id: str, log_dir: str):
        self._data: Dict[int, replication_pb2.DataItem] = {}
        self._update_history = deque(maxlen=100)  # Keep last 100 updates
        self.node_id = node_id
        self.current_version = 0
        self._logger = logging.getLogger(f"storage.{node_id}")

        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._log_dir / f"{node_id}_operations.jsonl"

    async def get(self, key: int) -> Optional[replication_pb2.DataItem]:
        return self._data.get(key)

    async def get_all(self) -> List[replication_pb2.DataItem]:
        return list(self._data.values())

    async def update(self, key: int, value: int, version: int) -> replication_pb2.DataItem:
        if key < 0 or version < 0:
            raise ValueError("Key and version must be non-negative")

        item = replication_pb2.DataItem(
            key=key,
            value=value,
            version=version
        )
        self._data[key] = item
        self._update_history.append(item)

        log_entry = {
            'operation': 'UPDATE',
            'timestamp': int(time.time()),
            'node_id': self.node_id,
            'key': key,
            'value': value,
            'version': version
        }

        with self._log_file.open('a') as f:
            json.dump(log_entry, f)
            f.write('\n')

        return item

    def get_next_version(self) -> int:
        self.current_version += 1
        return self.current_version

    def get_recent_updates(self, count: int) -> List[replication_pb2.DataItem]:
        """Get the most recent updates."""
        return list(self._update_history)[-count:]

    async def close(self):
        self._data.clear()
