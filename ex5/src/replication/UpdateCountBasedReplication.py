from src.proto import replication_pb2
from src.replication.BaseReplication import BaseReplication
import asyncio
from typing import List

class UpdateCountBasedReplication(BaseReplication):
    """Update count based replication for first layer nodes.

    Implements primary-backup, passive replication where:
    - Updates are propagated every N updates
    - Primary node propagates to backups
    - Lazy consistency model
    """

    def __init__(self, update_threshold: int = 10):
        """Initialize update count based replication.

        Args:
            update_threshold: Number of updates before triggering replication
        """
        super().__init__(propagation_type='passive', consistency_type='lazy')
        self.update_threshold = update_threshold
        self.update_count = 0
        self._sync_task = None

    async def handle_update(self, data_item: replication_pb2.DataItem) -> bool:
        """Handle an update, possibly triggering replication.

        Args:
            data_item: The data item to be replicated

        Returns:
            bool: True if update was handled successfully
        """
        try:
            self.update_count += 1

            if self.update_count >= self.update_threshold:
                await self.sync()
                self.update_count = 0

            return True

        except Exception as e:
            print(f"Error in update count based replication: {e}")
            return False

    async def sync(self) -> None:
        """Synchronize state with other nodes based on update count."""
        if not self.node.is_primary:
            return

        try:
            # Phase 1: Get updates from core
            status = await self.node.primary_stub.GetNodeStatus(replication_pb2.Empty())
            updates = []

            for item in status.current_data:
                current_item = self.node.store.get(item.key)
                if not current_item or current_item.version < item.version:
                    updates.append(item)

            if not updates:
                return

            # Phase 2: Prepare all backups
            prepare_responses = await asyncio.gather(*[
                stub.PrepareUpdate(replication_pb2.UpdateBatch(updates=updates))
                for stub in self.node.backup_stubs.values()
            ], return_exceptions=True)

            if not all(resp.success for resp in prepare_responses if not isinstance(resp, Exception)):
                # If any backup not ready, abort
                await self._abort_update()
                return

            # Phase 3: Apply updates atomically
            await self._apply_updates(updates)
            commit_responses = await asyncio.gather(*[
                stub.CommitUpdate(replication_pb2.Empty())
                for stub in self.node.backup_stubs.values()
            ], return_exceptions=True)

        except Exception as e:
            print(f"Error during count-based sync: {e}")
            await self._abort_update()

    async def _apply_updates(self, updates: List[replication_pb2.DataItem]):
        """Apply updates atomically to local store."""
        for item in updates:
            await self.node.store.update(
                key=item.key,
                value=item.value,
                version=item.version
            )
