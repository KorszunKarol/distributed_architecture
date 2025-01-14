import asyncio
import logging
import grpc
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
        self.node = None
        self._logger.info("Initialized eager replication strategy")

    def attach_node(self, node):
        """Attach this replication strategy to a node."""
        self.node = node
        self._logger.info(f"Attached to node {node.node_id}")

    async def sync(self) -> None:
        """Synchronize state with peers.

        For eager replication, sync is not needed as updates are
        propagated immediately.
        """
        self._logger.debug("Sync called - no action needed for eager replication")
        pass

    async def handle_update(self, update_request: replication_pb2.UpdateRequest):
        """Handle an update request."""
        try:
            data_item = update_request.update
            if not data_item:
                raise ValueError("No data item in update request")

            self._logger.info(
                f"Handling update for key={data_item.key}, "
                f"value={data_item.value}, "
                f"version={data_item.version}"
            )

            for peer_stub in self.node.peer_stubs.values():
                try:
                    notification = replication_pb2.UpdateNotification(
                        data=data_item,
                        source_node=self.node.node_id
                    )
                    await peer_stub.PropagateUpdate(notification)
                except Exception as e:
                    self._logger.error(f"Failed to propagate to peer: {e}")
                    raise

            return True
        except Exception as e:
            self._logger.error(f"Failed to handle update: {e}")
            raise

    async def _rollback(self, data_item: replication_pb2.DataItem) -> None:
        """Rollback a failed update."""
        try:
            self._logger.warning(f"Starting rollback for key={data_item.key}")
            self._logger.warning(f"Rolling back update for key {data_item.key}")
        except Exception as e:
            self._logger.error(f"Rollback failed: {e}", exc_info=True)

    async def PropagateUpdate(self, request: replication_pb2.UpdateNotification, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        """Handle update propagation from peer nodes.

        Args:
            request: The update notification from a peer
            context: The gRPC service context

        Returns:
            AckResponse indicating success or failure
        """
        update = request.data
        self._logger.info(f"Received update propagation from {request.source_node} for key={update.key}")

        try:
            self._logger.debug(f"Applying propagated update to local store: key={update.key}, value={update.value}, version={update.version}")
            await self.node.store.update(
                key=update.key,
                value=update.value,
                version=update.version
            )
            self._logger.info(f"Successfully applied propagated update for key={update.key}")
            return replication_pb2.AckResponse(success=True)
        except Exception as e:
            self._logger.error(f"Failed to apply propagated update: {e}", exc_info=True)
            return replication_pb2.AckResponse(success=False, message=str(e))
