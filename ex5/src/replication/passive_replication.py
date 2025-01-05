"""Passive replication strategy for first and second layers."""
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
        self.backup_stubs = []

    def set_backup_stubs(self, stubs: List) -> None:
        """Set the backup stubs after initialization.

        Args:
            stubs: List of gRPC stubs for backup nodes
        """
        self.backup_stubs = stubs
        self._logger.debug(f"Set {len(stubs)} backup stubs")

    async def sync(self) -> None:
        """Synchronize state with backup.

        For passive replication, sync is only needed when backup
        node reconnects after failure.
        """
        if not self.node or not hasattr(self.node, 'is_primary') or not self.node.is_primary:
            return

        try:
            updates = await self.node.store.get_all()
            if not updates or not self.backup_stubs:
                return

            notification = replication_pb2.UpdateGroup(
                updates=list(updates),  # Convert to list if it's not already
                source_node=self.node.node_id,
                layer=getattr(self.node, 'layer', 0),
                update_count=len(updates)
            )

            for stub in self.backup_stubs:
                try:
                    await stub.SyncUpdates(notification)
                    self._logger.info(f"Synced {len(updates)} updates to backup")
                except Exception as e:
                    self._logger.error(f"Failed to sync with backup: {e}")

        except Exception as e:
            self._logger.error(f"Sync failed: {e}")

    async def handle_update(self, update_group: replication_pb2.UpdateGroup) -> bool:
        """Handle updates from upper layer.

        Args:
            update_group: UpdateGroup containing data items to be replicated

        Returns:
            bool: True if updates were successfully handled
        """
        if not self.node or not hasattr(self.node, 'is_primary') or not self.node.is_primary:
            return False

        try:
            # First update local store
            for item in update_group.updates:
                await self.node.store.update(
                    key=item.key,
                    value=item.value,
                    version=item.version
                )

            # Then propagate to backups if available
            if self.backup_stubs:
                for stub in self.backup_stubs:
                    try:
                        await stub.SyncUpdates(update_group)
                        self._logger.info(f"Propagated {len(update_group.updates)} updates to backup")
                    except Exception as e:
                        self._logger.error(f"Failed to propagate to backup: {e}")
                        return False

            return True

        except Exception as e:
            self._logger.error(f"Failed to handle updates: {e}")
            return False