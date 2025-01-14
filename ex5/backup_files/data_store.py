"""Data store implementation with proper version logging."""
import json
import time
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from src.proto import replication_pb2

class DataStore:
    def __init__(self, node_id: str, log_dir: str):
        """Initialize the data store with proper logging."""
        self.node_id = node_id
        self.data: Dict[int, replication_pb2.DataItem] = {}
        self.key_versions: Dict[int, int] = {}

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.version_log_file = self.log_dir / f"{node_id}_versions.log"
        self.state_file = self.log_dir / f"{node_id}_state.json"

        self._load_state()

    def _load_state(self):
        """Load existing state if available."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    for key_str, item_dict in state.items():
                        key = int(key_str)
                        item = replication_pb2.DataItem(
                            key=key,
                            value=item_dict['value'],
                            version=item_dict['version'],
                            timestamp=item_dict['timestamp']
                        )
                        self.data[key] = item
                        self.key_versions[key] = item.version
            except Exception as e:
                print(f"Error loading state for {self.node_id}: {e}")

    def _get_next_version(self, key: int) -> int:
        """Get next version for a specific key."""
        if key not in self.key_versions:
            self.key_versions[key] = 1
            return 1
        self.key_versions[key] += 1
        return self.key_versions[key]

    async def update(self, key: int, value: int, version: Optional[int] = None) -> replication_pb2.DataItem:
        """Update or create a data item."""
        if version is None:
            version = self._get_next_version(key)

        item = replication_pb2.DataItem(
            key=key,
            value=value,
            version=version,
            timestamp=int(time.time())
        )

        self.data[key] = item
        self._log_version(item, "UPDATE")
        self._save_state()
        return item

    async def get_all(self) -> List[replication_pb2.DataItem]:
        """Get all data items."""
        future = asyncio.get_event_loop().create_future()
        future.set_result(list(self.data.values()))
        return await future

    async def get_recent_updates(self, count: int) -> List[replication_pb2.DataItem]:
        """Get the most recent updates, up to count."""
        sorted_items = sorted(
            self.data.values(),
            key=lambda x: x.version,
            reverse=True
        )
        future = asyncio.get_event_loop().create_future()
        future.set_result(sorted_items[:count])
        return await future

    async def get(self, key: int) -> Optional[replication_pb2.DataItem]:
        """Get data item by key."""
        item = self.data.get(key)
        if item:
            self._log_version(item, "READ")
        return item

    def _log_version(self, item: replication_pb2.DataItem, operation: str):
        """Log version information to the version log file."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = (f"{timestamp} - Key: {item.key}, Value: {item.value}, "
                    f"Version: {item.version}, Operation: {operation}\n")

        with open(self.version_log_file, 'a') as f:
            f.write(log_entry)

    def _save_state(self):
        """Save current state to JSON file."""
        state = {}
        for key, item in self.data.items():
            state[str(key)] = {
                'value': item.value,
                'version': item.version,
                'timestamp': item.timestamp
            }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    async def close(self):
        """Close the data store and save final state."""
        self._save_state()
