"""Second layer node implementing lazy, passive replication with primary-backup."""
from typing import Optional
import asyncio
import grpc
from src.node.base_node import BaseNode
from src.proto import replication_pb2, replication_pb2_grpc

class SecondLayerNode(BaseNode):
    """Second layer node that receives updates every 10 updates through passive replication.

    This node belongs to layer 1 and implements:
    - Primary-backup: One node is primary, others are backups
    - Passive replication: Primary processes updates and propagates to backups
    - Lazy replication: Syncs every 10 updates
    """

    def __init__(self,
                 node_id: str,
                 log_dir: str,
                 port: int,
                 primary_core_address: str,
                 is_primary: bool,
                 backup_addresses: list[str] = None):
        """Initialize second layer node."""
        super().__init__(node_id, layer=1, log_dir=log_dir, port=port)
        self.primary_core_address = primary_core_address
        self.is_primary = is_primary
        self.backup_addresses = backup_addresses or []

        # Connection to core node (only used by primary)
        self.primary_channel: Optional[grpc.aio.Channel] = None
        self.primary_stub: Optional[replication_pb2_grpc.NodeServiceStub] = None

        # Connections to backup nodes (only used by primary)
        self.backup_channels: dict[str, grpc.aio.Channel] = {}
        self.backup_stubs: dict[str, replication_pb2_grpc.NodeServiceStub] = {}

        # Connection to primary node (only used by backups)
        self.primary_node_channel: Optional[grpc.aio.Channel] = None
        self.primary_node_stub: Optional[replication_pb2_grpc.NodeServiceStub] = None

        self.last_update_count = 0
        self.sync_task = None
        self._closed = False

    async def start(self):
        """Start the node and sync loop."""
        print(f"Starting second layer node {self.node_id}")
        await super().start()
        print(f"Second layer node {self.node_id} server started")

        # Start connection and sync tasks without waiting
        if self.is_primary:
            # Primary connects to core node and backup nodes
            asyncio.create_task(self._connect_to_core())
            asyncio.create_task(self._connect_to_backups())
        else:
            # Backup nodes only connect to primary node
            asyncio.create_task(self._connect_to_primary())

        self.sync_task = asyncio.create_task(self._sync_loop())
        print(f"Second layer node {self.node_id} tasks created")
        return self

    async def _connect_to_core(self):
        """Connect to core node (primary only)."""
        while not self._closed:
            try:
                self.primary_channel = grpc.aio.insecure_channel(self.primary_core_address)
                await asyncio.wait_for(self.primary_channel.channel_ready(), timeout=2.0)
                self.primary_stub = replication_pb2_grpc.NodeServiceStub(self.primary_channel)
                print(f"Node {self.node_id} connected to core node")
                break
            except Exception as e:
                print(f"Node {self.node_id} failed to connect to core node: {e}")
                await asyncio.sleep(1)

    async def _connect_to_backups(self):
        """Connect to backup nodes (primary only)."""
        while not self._closed:
            for addr in self.backup_addresses:
                if addr != f'localhost:{self.port}' and addr not in self.backup_stubs:
                    try:
                        channel = grpc.aio.insecure_channel(addr)
                        await asyncio.wait_for(channel.channel_ready(), timeout=2.0)
                        self.backup_channels[addr] = channel
                        self.backup_stubs[addr] = replication_pb2_grpc.NodeServiceStub(channel)
                        print(f"Node {self.node_id} connected to backup {addr}")
                    except Exception as e:
                        print(f"Node {self.node_id} failed to connect to backup {addr}: {e}")
                        continue

            if len(self.backup_stubs) == len(self.backup_addresses) - 1:
                print(f"Node {self.node_id} connected to all backups")
                break

            await asyncio.sleep(1)

    async def _connect_to_primary(self):
        """Connect to primary node (backup only)."""
        while not self._closed:
            try:
                primary_addr = self.backup_addresses[0]
                self.primary_node_channel = grpc.aio.insecure_channel(primary_addr)
                await asyncio.wait_for(self.primary_node_channel.channel_ready(), timeout=2.0)
                self.primary_node_stub = replication_pb2_grpc.NodeServiceStub(self.primary_node_channel)
                print(f"Node {self.node_id} connected to primary node")
                break
            except Exception as e:
                print(f"Node {self.node_id} failed to connect to primary: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Stop the node and cleanup connections."""
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

    async def _sync_loop(self):
        """Sync with appropriate source every 10 updates."""
        while not self._closed:
            try:
                if self.is_primary:
                    if not self.primary_stub:
                        await asyncio.sleep(1)
                        continue

                    status = await self.primary_stub.GetNodeStatus(replication_pb2.Empty())

                    if status.update_count >= self.last_update_count + 10:
                        # Update primary's state
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

                        # Propagate updates to backups
                        if updates:
                            await self._propagate_to_backups(updates)

                        self.last_update_count = status.update_count
                else:
                    if not self.primary_node_stub:
                        await asyncio.sleep(1)
                        continue

                    status = await self.primary_node_stub.GetNodeStatus(replication_pb2.Empty())

                    if status.update_count >= self.last_update_count + 10:
                        for item in status.current_data:
                            current_item = self.store.get(item.key)
                            if not current_item or current_item.version < item.version:
                                await self.store.update(
                                    key=item.key,
                                    value=item.value,
                                    version=item.version
                                )
                        self.last_update_count = status.update_count

            except grpc.RpcError as rpc_error:
                print(f"RPC failed: {rpc_error.code()}, {rpc_error.details()}")
                if self.is_primary:
                    self.primary_stub = None
                else:
                    self.primary_node_stub = None
            except Exception as e:
                print(f"Error in sync loop: {e}")

            await asyncio.sleep(1)

    async def _propagate_to_backups(self, updates: list[replication_pb2.DataItem]):
        """Propagate updates to backup nodes (only called by primary)."""
        for backup_stub in self.backup_stubs.values():
            try:
                for item in updates:
                    notification = replication_pb2.UpdateNotification(
                        data=item,
                        source_node=self.node_id
                    )
                    await backup_stub.PropagateUpdate(notification)
            except Exception as e:
                print(f"Failed to propagate to backup: {e}")

    async def ExecuteTransaction(
        self,
        request: replication_pb2.Transaction,
        context: grpc.aio.ServicerContext
    ) -> replication_pb2.TransactionResponse:
        """Execute read-only transactions."""
        try:
            if request.type != replication_pb2.Transaction.READ_ONLY:
                raise Exception("Second layer nodes only accept read-only transactions")

            if request.target_layer != self.layer:
                raise Exception(f"Transaction targeted for layer {request.target_layer}, "
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

        except Exception as e:
            return replication_pb2.TransactionResponse(
                success=False,
                error_message=str(e)
            )