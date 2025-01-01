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
        self._logger.info("Initialized eager replication strategy")

    async def sync(self) -> None:
        """Synchronize state with peers.

        For eager replication, sync is not needed as updates are
        propagated immediately.
        """
        self._logger.debug("Sync called - no action needed for eager replication")
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
        self._logger.info(f"Handling update for key={data_item.key}, value={data_item.value}, version={data_item.version}")
        
        async with self._transaction_lock:
            try:
                # First update local store
                self._logger.debug(f"Updating local store for key={data_item.key}")
                await self.node.store.update(
                    key=data_item.key,
                    value=data_item.value,
                    version=data_item.version
                )
                self._logger.debug(f"Local store updated successfully for key={data_item.key}")

                # Then propagate to all peers
                if self.node.peer_stubs:
                    self._logger.debug(f"Propagating update to {len(self.node.peer_stubs)} peers")
                    notification = replication_pb2.UpdateNotification(
                        data=data_item,
                        source_node=self.node.node_id
                    )
                    
                    propagation_tasks = [
                        stub.PropagateUpdate(notification)
                        for stub in self.node.peer_stubs.values()
                    ]
                    
                    self._logger.debug("Waiting for peer acknowledgments")
                    responses = await asyncio.gather(*propagation_tasks, return_exceptions=True)
                    
                    # Check responses
                    success = True
                    for i, response in enumerate(responses):
                        if isinstance(response, Exception):
                            self._logger.error(f"Peer {i} failed with error: {response}")
                            success = False
                        elif not response.success:
                            self._logger.error(f"Peer {i} rejected update: {response.message}")
                            success = False
                    
                    if not success:
                        self._logger.warning("Rolling back due to peer propagation failure")
                        await self._rollback(data_item)
                        return False

                    self._logger.info(f"Successfully propagated update to all peers for key={data_item.key}")
                    return True
                else:
                    self._logger.info("No peers to propagate to, update considered successful")
                    return True

            except Exception as e:
                self._logger.error(f"Update failed with error: {e}", exc_info=True)
                await self._rollback(data_item)
                return False

    async def _rollback(self, data_item: replication_pb2.DataItem) -> None:
        """Rollback a failed update."""
        try:
            self._logger.warning(f"Starting rollback for key={data_item.key}")
            # Implement rollback logic here
            # For now, just log the attempt
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
