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
                # First update local store
                await self.node.store.update(
                    key=data_item.key,
                    value=data_item.value,
                    version=data_item.version
                )

                # Then propagate to all peers
                if self.node.peer_stubs:
                    notification = replication_pb2.UpdateNotification(
                        data=data_item,
                        source_node=self.node.node_id
                    )
                    responses = await asyncio.gather(*[
                        stub.PropagateUpdate(notification)
                        for stub in self.node.peer_stubs.values()
                    ])

                    if not all(r.success for r in responses):
                        await self._rollback(data_item)
                        return False

                return True

            except Exception as e:
                self._logger.error(f"Update failed: {e}")
                await self._rollback(data_item)
                return False

    async def _rollback(self, data_item: replication_pb2.DataItem) -> None:
        """Rollback a failed update."""
        try:
            # Implement rollback logic here
            # For now, just log the attempt
            self._logger.warning(f"Rolling back update for key {data_item.key}")
        except Exception as e:
            self._logger.error(f"Rollback failed: {e}")

    async def PropagateUpdate(self, request: replication_pb2.UpdateNotification) -> replication_pb2.AckResponse:
        """Propagate an update to all peers."""
        try:
            update = request.data
            await self.node.store.update(
                key=update.key,
                value=update.value,
                version=update.version
            )
            return replication_pb2.AckResponse(success=True)
        except Exception as e:
            return replication_pb2.AckResponse(success=False, message=str(e))
