import logging
from src.proto import replication_pb2

class Storage:
    def __init__(self, node_id: str, log_dir: str):
        self.node_id = node_id
        self.log_dir = log_dir
        self._data = {}
        self._logger = logging.getLogger(f"storage.{node_id}")

    async def update(self, key: int, value: str, version: int) -> None:
        self._data[key] = replication_pb2.DataItem(
            key=key,
            value=value,
            version=version
        )
        self._logger.debug(f"Updated key={key} with value={value}, version={version}")

    async def get(self, key: int) -> replication_pb2.DataItem:
        return self._data.get(key)

    async def get_all(self) -> list:
        return list(self._data.values())

    async def clear(self) -> None:
        self._data.clear()