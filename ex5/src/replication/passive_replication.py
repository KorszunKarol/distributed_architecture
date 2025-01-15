"""Passive replication strategy for first and second layers."""
import asyncio
import logging
from typing import List, Optional
from src.proto import replication_pb2
from src.replication.base_replication import BaseReplication
import time

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
        """Set the backup stubs after initialization."""
        self.backup_stubs = stubs
        self._logger.debug(f"Set {len(stubs)} backup stubs")

    async def sync(self) -> None:
        """Synchronize state with backup nodes.

        For passive replication, sync is called periodically to ensure
        backup nodes are up to date.
        """
        if not self.node or not hasattr(self.node, 'is_primary') or not self.node.is_primary:
            return

        try:
            # Get all current data
            updates = await self.node.store.get_all()
            if not updates or not self.backup_stubs:
                return

            # Create sync notification
            notification = replication_pb2.LayerSyncNotification(
                source_layer=self.node.layer,
                target_layer=self.node.layer,
                updates=list(updates),
                update_count=len(updates),
                sync_timestamp=int(time.time()),
                source_node=self.node.node_id
            )

            # Send to all backups
            for stub in self.backup_stubs:
                try:
                    await stub.NotifyLayerSync(notification)
                    self._logger.info(f"Synced {len(updates)} updates to backup")
                except Exception as e:
                    self._logger.error(f"Failed to sync with backup: {e}")

        except Exception as e:
            self._logger.error(f"Sync failed: {e}")

    async def get_updates_from_primary(self) -> List[replication_pb2.DataItem]:
        """Get all pending updates from the primary node."""
        try:
            # Get updates from primary node's store
            updates = await self.node.store.get_all()
            return updates
        except Exception as e:
            self._logger.error(f"Failed to get updates from primary: {e}")
            return []

    async def handle_update(self, update_group: replication_pb2.UpdateGroup) -> bool:
        """Handle updates in the passive replication strategy."""
        try:
            if not self.backup_stubs:
                return True  # No backups to propagate to

            # Convert each update in the group to an UpdateNotification
            for update in update_group.updates:
                notification = replication_pb2.UpdateNotification(
                    data=update,
                    source_node=self.node.node_id  # This ensures backup sees primary as source
                )

                for stub in self.backup_stubs:
                    try:
                        await stub.PropagateUpdate(notification)
                    except Exception as e:
                        self._logger.error(f"Failed to propagate to backup: {e}")
                        return False

            return True
        except Exception as e:
            self._logger.error(f"Failed to handle update: {e}")
            return False