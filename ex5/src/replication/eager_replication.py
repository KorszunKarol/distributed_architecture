import asyncio
import logging
from typing import List, Optional
from src.proto import replication_pb2
from src.replication.base_replication import BaseReplication

class EagerReplication(BaseReplication):
    """Eager replication strategy for core layer nodes.

    Implements update-everywhere, active replication where:
    - All nodes process the same operations
    - Updates are propagated immediately
    - Waits for acknowledgment from all nodes before proceeding
    """

    def __init__(self) -> None:
        """Initialize eager replication strategy."""
        super().__init__(propagation_type='active', consistency_type='eager')
        self._transaction_lock = asyncio.Lock()
        self._logger = logging.getLogger("replication.eager")
        self._propagation_timeout = 5.0

    async def sync(self) -> None:
        """Synchronize state with peers.

        For eager replication, sync is not needed as updates are
        propagated immediately.
        """
        pass  # No sync needed for eager replication

    async def handle_update(self, data_item: replication_pb2.DataItem) -> bool:
        """Handle an update with eager replication protocol.

        Implements two-phase update process:
        1. Propagate to all peers and wait for acknowledgments
        2. If all acknowledge, commit; otherwise rollback

        Args:
            data_item: The data item to be replicated

        Returns:
            bool: True if update was successfully propagated and applied
        """
        async with self._transaction_lock:
            try:
                # Phase 1: Propagate to peers
                success = await self._propagate_to_peers(data_item)
                if not success:
                    await self._rollback_update(data_item)
                    return False

                # Phase 2: Apply locally
                await self._apply_update(data_item)
                return True

            except Exception as e:
                self._logger.error(f"Update failed: {e}")
                await self._rollback_update(data_item)
                return False

    async def _propagate_to_peers(self, data_item: replication_pb2.DataItem) -> bool:
        """Propagate update to all peers and wait for acknowledgments."""
        if not self.node.peer_stubs:
            self._logger.warning("No peers available for propagation")
            return True

        notification = replication_pb2.UpdateNotification(
            data=data_item,
            source_node=self.node.node_id
        )

        try:
            responses = await asyncio.gather(*[
                peer_stub.PropagateUpdate(notification)
                for peer_stub in self.node.peer_stubs.values()
            ], timeout=self._propagation_timeout)

            success = all(response.success for response in responses)
            if not success:
                self._logger.error("Not all peers acknowledged update")
            return success

        except asyncio.TimeoutError:
            self._logger.error("Propagation timeout")
            return False

    async def _apply_update(self, data_item: replication_pb2.DataItem) -> None:
        """Apply update locally."""
        await self.node.store.update(
            key=data_item.key,
            value=data_item.value,
            version=data_item.version
        )

    async def _rollback_update(self, data_item: replication_pb2.DataItem) -> None:
        """Rollback a failed update."""
        try:
            previous = await self.node.store.get(data_item.key)
            if previous:
                rollback_notification = replication_pb2.UpdateNotification(
                    data=previous,
                    source_node=self.node.node_id
                )
                await asyncio.gather(*[
                    peer_stub.PropagateUpdate(rollback_notification)
                    for peer_stub in self.node.peer_stubs.values()
                ])
                self._logger.info(f"Rolled back update for key {data_item.key}")
        except Exception as e:
            self._logger.error(f"Rollback failed: {e}")
