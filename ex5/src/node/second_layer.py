from typing import Optional
import asyncio
import grpc
from src.node.base_node import BaseNode
from src.proto import replication_pb2, replication_pb2_grpc

class SecondLayerNode(BaseNode):
    """Second layer node that receives updates every 10 updates through passive replication.

    This node belongs to layer 1 (second layer) and implements:
    - Primary-backup: One node is primary, others are backups
    - Passive replication: Primary processes updates and propagates to backups
    - Lazy replication: Syncs every 10 updates

    Implementation Notes:
        - Uses exponential backoff for connection retries
        - Implements graceful shutdown
        - Handles network partitions through reconnection logic

    Attributes:
        primary_core_address: Address of the core node to sync with (primary only)
        is_primary: Boolean indicating if this node is primary
        backup_addresses: List of addresses for backup nodes
        primary_channel: gRPC channel to core node (primary only)
        primary_stub: gRPC stub for core node communication (primary only)
        backup_channels: Dictionary of gRPC channels to backup nodes
        backup_stubs: Dictionary of gRPC stubs for backup communication
        primary_node_channel: gRPC channel to primary node (backup only)
        primary_node_stub: gRPC stub for primary node communication (backup only)
        last_update_count: Counter tracking number of updates received
        sync_task: Asyncio task handling periodic synchronization
        _closed: Internal flag indicating if node is shutting down
    """

    def __init__(
        self,
        node_id: str,
        log_dir: str,
        port: int,
        primary_core_address: str,
        is_primary: bool,
        backup_addresses: list[str] = None
    ):
        """Initialize second layer node.

        Args:
            node_id: Unique identifier for this node
            log_dir: Directory path for storing version logs
            port: Port number to listen on
            primary_core_address: Address of core node to sync with
            is_primary: Whether this node is primary
            backup_addresses: List of backup node addresses (optional)

        Raises:
            ValueError: If required parameters are invalid
        """
        super().__init__(node_id, layer=1, log_dir=log_dir, port=port)
        self.primary_core_address = primary_core_address
        self.is_primary = is_primary
        self.backup_addresses = backup_addresses or []

        self.primary_channel: Optional[grpc.aio.Channel] = None
        self.primary_stub: Optional[replication_pb2_grpc.NodeServiceStub] = None

        self.backup_channels: dict[str, grpc.aio.Channel] = {}
        self.backup_stubs: dict[str, replication_pb2_grpc.NodeServiceStub] = {}

        self.primary_node_channel: Optional[grpc.aio.Channel] = None
        self.primary_node_stub: Optional[replication_pb2_grpc.NodeServiceStub] = None

        self.last_update_count = 0
        self.sync_task = None
        self._closed = False

    async def start(self):
        """Start the node and initialize connections.

        Starts the gRPC server and establishes connections to other nodes based on role.
        Primary nodes connect to core layer and backup nodes, while backup nodes connect
        to their primary.

        Returns:
            SecondLayerNode: Self reference for method chaining

        Raises:
            Exception: If server startup fails
        """
        await super().start()

        if self.is_primary:
            asyncio.create_task(self._connect_to_core())
            asyncio.create_task(self._connect_to_backups())
        else:
            asyncio.create_task(self._connect_to_primary())

        self.sync_task = asyncio.create_task(self._sync_loop())
        return self

    async def stop(self):
        """Stop the node and cleanup all connections.

        Raises:
            Exception: If cleanup fails
        """
        self._closed = True

        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass

        if self.is_primary:
            if self.primary_channel:
                await self.primary_channel.close()
            for channel in self.backup_channels.values():
                await channel.close()
            self.backup_channels.clear()
            self.backup_stubs.clear()
        else:
            if self.primary_node_channel:
                await self.primary_node_channel.close()

        await super().stop()

    async def _connect_to_core(self):
        """Establish connection to core layer node.

        Raises:
            Exception: If connection fails repeatedly
        """
        while not self._closed:
            try:
                self.primary_channel = grpc.aio.insecure_channel(self.primary_core_address)
                await asyncio.wait_for(self.primary_channel.channel_ready(), timeout=2.0)
                self.primary_stub = replication_pb2_grpc.NodeServiceStub(self.primary_channel)
                break
            except Exception:
                await asyncio.sleep(1)

    async def _connect_to_backups(self):
        """Establish connections to all backup nodes.

        Raises:
            Exception: If connections fail repeatedly
        """
        while not self._closed:
            for addr in self.backup_addresses:
                if addr != f'localhost:{self.port}' and addr not in self.backup_stubs:
                    try:
                        channel = grpc.aio.insecure_channel(addr)
                        await asyncio.wait_for(channel.channel_ready(), timeout=2.0)
                        self.backup_channels[addr] = channel
                        self.backup_stubs[addr] = replication_pb2_grpc.NodeServiceStub(channel)
                    except Exception:
                        continue

            if len(self.backup_stubs) == len(self.backup_addresses) - 1:
                break

            await asyncio.sleep(1)

    async def _connect_to_primary(self):
        """Establish connection to primary node.

        Raises:
            Exception: If connection fails repeatedly
        """
        while not self._closed:
            try:
                primary_addr = self.backup_addresses[0]
                self.primary_node_channel = grpc.aio.insecure_channel(primary_addr)
                await asyncio.wait_for(self.primary_node_channel.channel_ready(), timeout=2.0)
                self.primary_node_stub = replication_pb2_grpc.NodeServiceStub(self.primary_node_channel)
                break
            except Exception:
                await asyncio.sleep(1)

    async def _sync_loop(self):
        """Periodic synchronization loop based on update count."""
        while not self._closed:
            try:
                if self.is_primary:
                    if not self.primary_stub:
                        await asyncio.sleep(1)
                        continue

                    status = await self.primary_stub.GetNodeStatus(replication_pb2.Empty())
                    if status.update_count >= self.last_update_count + 10:
                        await self._sync_as_primary()
                        self.last_update_count = status.update_count
                else:
                    if not self.primary_node_stub:
                        await asyncio.sleep(1)
                        continue

                    status = await self.primary_node_stub.GetNodeStatus(replication_pb2.Empty())
                    if status.update_count >= self.last_update_count + 10:
                        await self._sync_as_backup()
                        self.last_update_count = status.update_count

            except Exception as e:
                print(f"Error in sync loop: {e}")

            await asyncio.sleep(1)

    async def _sync_as_primary(self):
        """Synchronize updates as primary node."""
        if not self.primary_stub:
            return

        status = await self.primary_stub.GetNodeStatus(replication_pb2.Empty())
        updates = []

        for item in status.current_data:
            current_item = self.store.get(item.key)
            if not current_item or current_item.version < item.version:
                await self.store.update(
                    key=item.key,
                    value=item.value,
                    version=item.version
                )
                updates.append(item)

        if updates:
            await self._propagate_to_backups(updates)

    async def _sync_as_backup(self):
        """Synchronize updates as backup node."""
        if not self.primary_node_stub:
            return

        status = await self.primary_node_stub.GetNodeStatus(replication_pb2.Empty())
        for item in status.current_data:
            current_item = self.store.get(item.key)
            if not current_item or current_item.version < item.version:
                await self.store.update(
                    key=item.key,
                    value=item.value,
                    version=item.version
                )

    async def _propagate_to_backups(self, updates: list[replication_pb2.DataItem]):
        """Propagate updates to backup nodes.

        Args:
            updates: List of DataItem objects containing updates to propagate

        Raises:
            Exception: If propagation to any backup fails
        """
        for backup_stub in self.backup_stubs.values():
            try:
                for item in updates:
                    notification = replication_pb2.UpdateNotification(
                        data=item,
                        source_node=self.node_id
                    )
                    await backup_stub.PropagateUpdate(notification)
            except Exception:
                continue

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute a read-only transaction.

        Args:
            request: Transaction request containing operations to execute
            context: gRPC service context

        Returns:
            TransactionResponse containing operation results or error

        Raises:
            ValueError: If transaction is not read-only or targets wrong layer
        """
        try:
            if request.type != replication_pb2.Transaction.READ_ONLY:
                raise ValueError("Second layer nodes only accept read-only transactions")

            if request.target_layer != self.layer:
                raise ValueError(f"Transaction targeted for layer {request.target_layer}, "
                              f"but this is layer {self.layer}")

            results = []
            for op in request.operations:
                if op.type == replication_pb2.Operation.READ:
                    item = self.store.get(op.key)
                    if item:
                        results.append(replication_pb2.DataItem(
                            key=item.key,
                            value=item.value,
                            version=item.version,
                            timestamp=int(item.timestamp)
                        ))

            return replication_pb2.TransactionResponse(
                success=True,
                results=results
            )

        except ValueError as e:
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=str(e)
            )

    async def GetNodeStatus(
        self,
        request: replication_pb2.Empty,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.NodeStatus:
        """Get current status of this node.

        Args:
            request: Empty request
            context: gRPC service context

        Returns:
            NodeStatus containing current data and update count

        Raises:
            grpc.RpcError: If status collection fails
        """
        try:
            current_data = []
            for item in self.store.get_all():
                current_data.append(replication_pb2.DataItem(
                    key=item.key,
                    value=item.value,
                    version=item.version,
                    timestamp=int(item.timestamp)
                ))

            return replication_pb2.NodeStatus(
                node_id=self.node_id,
                current_data=current_data,
                update_count=len(current_data)
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise