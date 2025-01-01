"""Data store implementation for version management."""
from typing import Dict, Optional, List, Deque
import time
from pathlib import Path
import json
import logging
from src.proto import replication_pb2
from collections import deque

class DataStore:
    """Stores versioned data items and maintains a version log."""

    def __init__(self, node_id: str, log_dir: str):
        self._data: Dict[int, replication_pb2.DataItem] = {}
        self._update_history: Deque[replication_pb2.DataItem] = deque(maxlen=100)
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # System log file for general operations
        self._log_file = self._log_dir / f"{node_id}_data.jsonl"
        
        # Version history file for tracking all versions
        self._version_file = self._log_dir / f"{node_id}_version_history.jsonl"
        
        self.node_id = node_id
        self.current_version = 0
        self._logger = logging.getLogger(f"storage.{node_id}")
        self._logger.info(f"Initializing data store for node {node_id} with log file {self._log_file}")

    async def get(self, key: int) -> Optional[replication_pb2.DataItem]:
        """Get a data item by key."""
        self._logger.debug(f"Getting value for key={key}")
        item = self._data.get(key)
        if item:
            self._logger.debug(f"Found value for key={key}: version={item.version}, value={item.value}")
        else:
            self._logger.debug(f"No value found for key={key}")
        return item

    async def get_all(self) -> List[replication_pb2.DataItem]:
        """Get all data items."""
        items = list(self._data.values())
        self._logger.debug(f"Retrieved all {len(items)} data items")
        return items

    async def update(self, key: int, value: int, version: int) -> replication_pb2.DataItem:
        """Update or create a data item.
        
        Args:
            key: The key of the data item
            value: The value to store
            version: The version number of the update
            
        Returns:
            The updated data item
            
        Raises:
            ValueError: If key or version is invalid
        """
        if key < 0:
            raise ValueError(f"Invalid key: {key}. Key must be non-negative.")
        if version < 0:
            raise ValueError(f"Invalid version: {version}. Version must be non-negative.")
            
        self._logger.info(f"Updating key={key} with value={value} and version={version}")
        
        try:
            item = replication_pb2.DataItem(
                key=key,
                value=value,
                version=version,
                timestamp=int(time.time())
            )
            self._data[key] = item
            self._update_history.append(item)
            
            # Log the update to both files
            log_entry = {
                'key': item.key,
                'value': item.value,
                'version': item.version,
                'timestamp': item.timestamp,
                'node_id': self.node_id
            }
            
            self._logger.debug(f"Writing log entries: {log_entry}")
            try:
                # Write to version history file
                with self._version_file.open('a') as f:
                    json.dump(log_entry, f)
                    f.write('\n')
                
                # Write to system log file
                with self._log_file.open('a') as f:
                    json.dump(log_entry, f)
                    f.write('\n')
                    
                self._logger.debug("Successfully wrote to log files")
            except Exception as e:
                self._logger.error(f"Failed to write to log files: {e}", exc_info=True)
                raise

            self._logger.info(f"Successfully updated key={key} to version={version}")
            return item
            
        except Exception as e:
            self._logger.error(f"Failed to update key={key}: {e}", exc_info=True)
            raise

    def get_next_version(self) -> int:
        """Get the next version number."""
        self.current_version += 1
        self._logger.debug(f"Generated new version number: {self.current_version}")
        return self.current_version

    def get_recent_updates(self, count: int) -> List[replication_pb2.DataItem]:
        """Get the most recent updates in order."""
        updates = list(self._update_history)[-count:]
        self._logger.debug(f"Retrieved {len(updates)} recent updates")
        return updates

    async def close(self):
        """Close the data store."""
        self._logger.info("Closing data store")
        # Add any cleanup if needed in the future
