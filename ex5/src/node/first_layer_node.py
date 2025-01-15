"""First layer node implementation."""
import asyncio
import logging
import grpc
from typing import Optional, List
from src.proto import replication_pb2, replication_pb2_grpc
from src.node.base_node import BaseNode
from src.replication.passive_replication import PassiveReplication
import time

class FirstLayerNode(BaseNode):
    def __init__(
        self,
        node_id: str,
        port: int,
        is_primary: bool = False,
        backup_addresses: List[str] = None,
        second_layer_address: Optional[str] = None
    ):
        log_dir = f"logs/{node_id.lower()}"
        replication = PassiveReplication()

        super().__init__(
            node_id=node_id,
            layer=1,
            log_dir=log_dir,
            port=port,
            replication_strategy=replication
        )

        self.is_primary = is_primary
        self.backup_addresses = backup_addresses or []
        self.second_layer_address = second_layer_address
        self.backup_stubs = {}
        self.second_layer_stub = None
        self._logger = logging.getLogger(f"node.first_layer.{node_id}")
        self._last_sync_time = time.time()
        self._sync_interval = 10.0
        self._sync_task = None
        self._pending_updates = []
        self._logger.info(f"Initializing first layer node {node_id} (primary={is_primary})")
        if backup_addresses:
            self._logger.info(f"Configured with backups at {', '.join(backup_addresses)}")
        if second_layer_address:
            self._logger.info(f"Configured with second layer at {second_layer_address}")

    async def start(self):
        self._logger.info(f"Starting first layer node {self.node_id}")
        await super().start()

        # Connect to backup nodes regardless of primary status
        if self.backup_addresses:
            self._logger.debug(f"Connecting to nodes at {', '.join(self.backup_addresses)}")
            for addr in self.backup_addresses:
                await self._connect_to_backup(addr)

        # Connect to second layer and start time-based sync
        if self.second_layer_address and self.is_primary:
            self._logger.debug(f"Connecting to second layer at {self.second_layer_address}")
            await self._connect_to_second_layer()
            # Start the time-based sync loop for C layer
            self._sync_task = asyncio.create_task(self._time_sync_loop())
            self._logger.info("Started time sync loop for second layer")

        self._logger.info(f"First layer node {self.node_id} started successfully")

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        tx_type = "READ_ONLY" if request.type == replication_pb2.Transaction.READ_ONLY else "UPDATE"
        self._logger.info(f"Received {tx_type} transaction with {len(request.operations)} operations")

        if request.type == replication_pb2.Transaction.UPDATE:
            error_msg = "Write operations not allowed"
            self._logger.warning(f"Rejected {tx_type} transaction: {error_msg}")
            raise Exception(error_msg)

        for op in request.operations:
            if op.HasField('write'):
                error_msg = "Write operations not allowed"
                self._logger.warning(f"Rejected transaction with write operation: {error_msg}")
                raise Exception(error_msg)

        results = []
        try:
            for i, op in enumerate(request.operations):
                if op.HasField('read'):
                    self._logger.debug(f"Processing read operation {i+1}/{len(request.operations)}: key={op.read.key}")
                    item = await self.store.get(op.read.key)
                    if item:
                        self._logger.debug(f"Found value for key={op.read.key}: version={item.version}")
                        results.append(item)
                    else:
                        self._logger.debug(f"No value found for key={op.read.key}")

            self._logger.info(f"Successfully completed read transaction with {len(results)} results")
            return replication_pb2.TransactionResponse(success=True, results=results)
        except Exception as e:
            self._logger.error(f"Read transaction failed: {e}", exc_info=True)
            raise

    async def SyncUpdates(self, request: replication_pb2.UpdateGroup, context: grpc.aio.ServicerContext) -> replication_pb2.AckResponse:
        """Handle updates from core layer (A nodes)."""
        source_node = request.source_node

        # If we're a backup node (B2), reject direct updates from A nodes
        if not self.is_primary and source_node.startswith('A'):
            error_msg = f"Backup node cannot accept updates directly from core layer: {source_node}"
            return replication_pb2.AckResponse(success=False, message=error_msg)

        self._logger.info(f"Received sync request from {source_node} with {len(request.updates)} updates")
        try:
            # Store updates locally
            for update in request.updates:
                await self.store.update(
                    key=update.key,
                    value=update.value,
                    version=update.version
                )
                self._logger.debug(f"Stored update for key={update.key}")

                # Update monitoring stats
                self.websocket_client.increment_update_count()
                self.websocket_client.update_sync_time()

            # If primary, propagate immediately to backup nodes (B2)
            if self.is_primary and self.backup_stubs:
                self._logger.debug(f"Propagating {len(request.updates)} updates to backups")
                success = await self.replication.handle_update(request)
                if not success:
                    error_msg = "Failed to propagate to backups"
                    self._logger.error(error_msg)
                    return replication_pb2.AckResponse(success=False, message=error_msg)
                self._logger.info(f"Successfully propagated {len(request.updates)} updates to backups")

            return replication_pb2.AckResponse(success=True)

        except Exception as e:
            error_msg = f"Failed to sync updates: {e}"
            self._logger.error(error_msg, exc_info=True)
            return replication_pb2.AckResponse(success=False, message=error_msg)

    async def _connect_to_backup(self, address: str) -> None:
        """Connect to a backup node with retries."""
        max_retries = 5
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                self._logger.debug(f"Creating channel to node at {address}")
                channel = grpc.aio.insecure_channel(address)
                stub = replication_pb2_grpc.NodeServiceStub(channel)

                # Try to get node status
                empty = replication_pb2.Empty()
                await stub.GetNodeStatus(empty)

                self._logger.info(f"Connected to backup at {address}")
                self.backup_stubs[address] = stub
                self.replication.set_backup_stubs(list(self.backup_stubs.values()))
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    self._logger.debug(f"Attempt {attempt + 1} failed to connect to backup {address}: {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    self._logger.warning(f"Failed to connect to backup at {address} after {max_retries} attempts")

    async def _connect_to_second_layer(self) -> None:
        """Connect to second layer node with retries."""
        max_retries = 5
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                self._logger.debug(f"Connecting to second layer at {self.second_layer_address}")
                channel = grpc.aio.insecure_channel(self.second_layer_address)
                self.second_layer_stub = replication_pb2_grpc.NodeServiceStub(channel)

                # Verify connection
                empty = replication_pb2.Empty()
                await self.second_layer_stub.GetNodeStatus(empty)

                self._logger.info(f"Connected to second layer at {self.second_layer_address}")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    self._logger.debug(f"Attempt {attempt + 1} failed to connect to second layer: {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    self._logger.warning(f"Failed to connect to second layer after {max_retries} attempts")

    async def _time_sync_loop(self) -> None:
        """Time-based sync loop for second layer propagation (every 10 seconds)."""
        self._logger.info("Starting time sync loop for second layer")
        while True:
            try:
                await asyncio.sleep(self._sync_interval)
                current_time = time.time()

                if current_time - self._last_sync_time >= self._sync_interval:
                    self._logger.info("Time sync interval reached (10s), notifying second layer")
                    await self._notify_second_layer()
                    self._last_sync_time = current_time

            except asyncio.CancelledError:
                self._logger.info("Stopping time sync loop")
                break
            except Exception as e:
                self._logger.error(f"Time sync loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _notify_second_layer(self) -> None:
        """Notify second layer of updates."""
        try:
            self._logger.info("Preparing updates for second layer notification")
            updates = await self.store.get_all()

            if updates:
                self._logger.info(f"Sending {len(updates)} updates to second layer")
                for update in updates:
                    self._logger.debug(f"Update: key={update.key}, value={update.value}, "
                                     f"version={update.version}")

                notification = replication_pb2.UpdateGroup(
                    updates=updates,
                    source_node=self.node_id,
                    layer=1,
                    update_count=len(updates)
                )

                if self.second_layer_stub:
                    try:
                        response = await self.second_layer_stub.SyncUpdates(notification)
                        self._logger.info(f"Second layer response: {response.success} - {response.message}")
                    except Exception as e:
                        self._logger.error(f"Failed to notify second layer: {e}")
                        await self._connect_to_second_layer()
                else:
                    self._logger.warning("No second layer connection available")
                    await self._connect_to_second_layer()

        except Exception as e:
            self._logger.error(f"Failed to notify second layer: {e}", exc_info=True)
            await self._connect_to_second_layer()

    async def _periodic_sync(self):
        """Periodically sync with second layer every 10 seconds."""
        while True:
            try:
                await asyncio.sleep(10)
                self._logger.debug("Time sync interval reached, notifying second layer")
                await self._notify_second_layer()

            except asyncio.CancelledError:
                self._logger.info("Stopping periodic sync")
                break
            except Exception as e:
                self._logger.error(f"Error in periodic sync: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def PropagateUpdate(
        self,
        request: replication_pb2.UpdateNotification,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.AckResponse:
        """Handle update propagation from primary node."""


        try:
            # Store the update locally
            data = request.data
            await self.store.update(
                key=data.key,
                value=data.value,
                version=data.version
            )

            # Update monitoring stats
            self.websocket_client.increment_update_count()
            self.websocket_client.update_sync_time()

            self._logger.info(f"Successfully processed update for key={data.key}")
            return replication_pb2.AckResponse(success=True)

        except Exception as e:
            error_msg = f"Failed to handle propagated update: {e}"
            self._logger.error(error_msg, exc_info=True)
            return replication_pb2.AckResponse(success=False, message=error_msg)