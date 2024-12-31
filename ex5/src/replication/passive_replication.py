import asyncio
import logging
import time
from typing import List
from src.proto import replication_pb2
from src.replication.base_replication import BaseReplication

class PassiveReplication(BaseReplication):
    """Passive replication strategy for first and second layers.

    Implements primary-backup replication where:
    - Primary receives and processes updates
    - Primary propagates to backup immediately
    """

    def __init__(self) -> None:
        super().__init__(propagation_type='passive', consistency_type='lazy')
        self._logger = logging.getLogger("replication.passive")

    async def sync(self) -> None:
        """Synchronize state with backup.

        For passive replication, sync is only needed when backup
        node reconnects after failure.
        """
        if not self.node.is_primary:
            return

        try:
            updates = await self.node.store.get_all()
            if updates and self.node.backup_stub:
                notification = replication_pb2.UpdateGroup(
                    updates=updates,
                    source_node=self.node.node_id,
                    layer=self.node.layer,
                    update_count=len(updates)
                )
                await self.node.backup_stub.SyncUpdates(notification)
                self._logger.info(f"Synced {len(updates)} updates to backup")
        except Exception as e:
            self._logger.error(f"Sync failed: {e}")

    async def handle_update(self, updates: List[replication_pb2.DataItem]) -> bool:
        """Handle updates from upper layer."""
        if not self.node.is_primary:
            return False

        try:
            for item in updates:
                await self.node.store.update(
                    key=item.key,
                    value=item.value,
                    version=item.version
                )
            await self._propagate_to_backup(updates)
            return True
        except Exception as e:
            self._logger.error(f"Failed to handle updates: {e}")
            return False

    async def _propagate_to_backup(self, updates: List[replication_pb2.DataItem]) -> None:
        """Propagate updates to backup node."""
        if not self.node.is_primary or not self.node.backup_stub:
            return

        try:
            notification = replication_pb2.UpdateGroup(
                updates=updates,
                source_node=self.node.node_id,
                layer=self.node.layer,
                update_count=len(updates)
            )

            await self.node.backup_stub.SyncUpdates(notification)
            self._logger.info(f"Propagated {len(updates)} updates to backup")

        except Exception as e:
            self._logger.error(f"Failed to propagate to backup: {e}")