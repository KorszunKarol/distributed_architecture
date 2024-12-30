import asyncio
import time
from src.proto import replication_pb2
from src.replication.BaseReplication import BaseReplication

class TimeBasedReplication(BaseReplication):
    """Time based replication for second layer nodes.

    Implements primary-backup, passive replication where:
    - Updates are propagated every N seconds
    - Primary node propagates to backups
    - Lazy consistency model
    """

    def __init__(self, time_interval: int = 10):
        """Initialize time based replication.

        Args:
            time_interval: Seconds between synchronizations
        """
        super().__init__(propagation_type='passive', consistency_type='lazy')
        self.time_interval = time_interval
        self.last_sync_time = 0
        self._sync_task = None

    async def start(self) -> None:
        """Start the periodic sync task."""
        await super().start()
        self._sync_task = asyncio.create_task(self._sync_loop())

    async def stop(self) -> None:
        """Stop the periodic sync task."""
        await super().stop()
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

    async def handle_update(self, data_item: replication_pb2.DataItem) -> bool:
        """Handle an update, sync happens on time interval.

        Args:
            data_item: The data item to be replicated

        Returns:
            bool: True if update was handled successfully
        """
        return True  # Updates are handled by periodic sync

    async def sync(self) -> None:
        """Synchronize state with other nodes."""
        if not self.node.is_primary:
            return

        try:
            status = await self.node.primary_stub.GetNodeStatus(replication_pb2.Empty())
            updates = []

            for item in status.current_data:
                current_item = self.node.store.get(item.key)
                if not current_item or current_item.version < item.version:
                    await self.node.store.update(
                        key=item.key,
                        value=item.value,
                        version=item.version
                    )
                    updates.append(item)

            if updates:
                await self.node._propagate_to_backups(updates)

            self.last_sync_time = time.time()

        except Exception as e:
            print(f"Error during time-based sync: {e}")

    async def _sync_loop(self) -> None:
        """Run periodic synchronization."""
        while self._running:
            current_time = time.time()
            if current_time - self.last_sync_time >= self.time_interval:
                await self.sync()
            await asyncio.sleep(1)
