import asyncio
from typing import List
import grpc
from src.proto import replication_pb2
from src.replication.BaseReplication import BaseReplication

class EagerReplication(BaseReplication):
    """Eager replication strategy for core layer nodes.

    Implements update-everywhere, active replication where:
    - All nodes process the same operations
    - Updates are propagated immediately
    - Waits for acknowledgment from all nodes
    """

    def __init__(self):
        """Initialize eager replication strategy."""
        super().__init__(propagation_type='active', consistency_type='eager')
        self._sequence_number = 0
        self._transaction_lock = asyncio.Lock()

    async def handle_update(self, data_item: replication_pb2.DataItem) -> bool:
        """Handle an update with eager replication.

        Args:
            data_item: The data item to be replicated

        Returns:
            bool: True if update was successfully propagated to all peers
        """
        try:
            async with self._transaction_lock:
                self._sequence_number += 1

                notification = replication_pb2.UpdateNotification(
                    data=data_item,
                    source_node=self.node.node_id
                )

                responses = await asyncio.gather(*[
                    stub.PropagateUpdate(notification)
                    for stub in self.node.peer_stubs.values()
                ], return_exceptions=True)

                for response in responses:
                    if isinstance(response, Exception) or not response.success:
                        return False

                return True

        except Exception as e:
            print(f"Error in eager replication: {e}")
            return False

    async def sync(self) -> None:
        """Synchronize state with peers.

        For eager replication, sync is not needed as updates are
        propagated immediately.
        """
        pass  # No periodic sync needed for eager replication
