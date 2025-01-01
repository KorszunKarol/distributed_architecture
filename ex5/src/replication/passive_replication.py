import asyncio
import logging
from typing import List, Optional
from src.proto import replication_pb2
from src.replication.base_replication import BaseReplication

class PassiveReplication(BaseReplication):
    """Passive replication strategy for first and second layers.

    Implements primary-backup replication where:
    - Primary receives and processes updates
    - Primary propagates to backup immediately
    """

    def __init__(self) -> None:
        """Initialize passive replication strategy."""
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
                    layer=getattr(self.node, 'layer', 0),
                    update_count=len(updates)
                )
                await self.node.backup_stub.SyncUpdates(notification)
                self._logger.info(f"Synced {len(updates)} updates to backup")
        except Exception as e:
            self._logger.error(f"Sync failed: {e}")

    async def handle_update(self, updates: List[replication_pb2.DataItem]) -> bool:
        """Handle updates from upper layer.

        Args:
            updates: List of data items to be replicated

        Returns:
            bool: True if updates were successfully handled
        """
        if not self.node.is_primary:
            return False

        try:
            # First update local store
            for item in updates:
                await self.node.store.update(
                    key=item.key,
                    value=item.value,
                    version=item.version
                )

            # Then propagate to backup if available
            if self.node.backup_stub:
                try:
                    notification = replication_pb2.UpdateGroup(
                        updates=updates,
                        source_node=self.node.node_id,
                        layer=getattr(self.node, 'layer', 0),
                        update_count=len(updates)
                    )
                    await self.node.backup_stub.SyncUpdates(notification)
                    self._logger.info(f"Propagated {len(updates)} updates to backup")
                except Exception as e:
                    self._logger.error(f"Failed to propagate to backup: {e}")
                    return False

            return True

        except Exception as e:
            self._logger.error(f"Failed to handle updates: {e}")
            return False