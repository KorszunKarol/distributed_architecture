"""Integration tests for layer interactions."""
import pytest
import asyncio
from unittest.mock import AsyncMock
from src.node.core_node import CoreNode
from src.node.first_layer_node import FirstLayerNode
from src.node.second_layer_node import SecondLayerNode
from src.proto import replication_pb2

@pytest.fixture
async def core_node(temp_log_dir):
    """Create and start a core node."""
    node = CoreNode(
        node_id="core_node",
        log_dir=str(temp_log_dir),
        port=50051,
        peer_addresses=["localhost:50052", "localhost:50053"],
        is_first_node=True,
        first_layer_address="localhost:50054"
    )
    await node.start()
    node.first_layer_stub = AsyncMock()
    node.first_layer_stub.SyncUpdates = AsyncMock(
        return_value=replication_pb2.UpdateResponse(success=True)
    )
    yield node
    await node.stop()

@pytest.fixture
async def first_layer_node(temp_log_dir):
    """Create and start a first layer node."""
    node = FirstLayerNode(
        node_id="first_layer_node",
        log_dir=str(temp_log_dir),
        port=50052,
        is_primary=True,
        backup_address="localhost:50053",
        second_layer_address="localhost:50054"
    )
    await node.start()
    node.second_layer_stub = AsyncMock()
    node.second_layer_stub.SyncUpdates = AsyncMock(
        return_value=replication_pb2.UpdateResponse(success=True)
    )
    yield node
    await node.stop()

@pytest.fixture
async def second_layer_node(temp_log_dir):
    """Create and start a second layer node."""
    node = SecondLayerNode(
        node_id="second_layer_node",
        log_dir=str(temp_log_dir),
        port=50053,
        is_primary=True,
        backup_address="localhost:50054"
    )
    await node.start()
    yield node
    await node.stop()

@pytest.mark.asyncio
class TestLayerInteraction:
    """Test suite for interactions between different layers."""

    async def test_core_to_first_layer_propagation(self, core_node, first_layer_node):
        """Test update propagation from core to first layer."""
        # Create and execute write transactions
        for i in range(10):  # Execute 10 updates to trigger propagation
            transaction = replication_pb2.Transaction(
                operations=[
                    replication_pb2.Operation(type=replication_pb2.Operation.WRITE, key=i, value=i*100)
                ]
            )
            result = await core_node.ExecuteTransaction(transaction, None)
            assert result.success

        # Verify first layer was notified
        assert core_node.first_layer_stub.SyncUpdates.called
        call_args = core_node.first_layer_stub.SyncUpdates.call_args[0][0]
        assert call_args.source_node == core_node.node_id
        assert call_args.layer == 0
        assert len(call_args.updates) > 0

    async def test_first_to_second_layer_propagation(self, first_layer_node, second_layer_node):
        """Test update propagation from first to second layer."""
        # Simulate updates from core layer
        updates = [
            replication_pb2.DataItem(key=i, value=i*100, version=1)
            for i in range(10)
        ]
        update_group = replication_pb2.UpdateGroup(
            source_node="core_node",
            layer=0,
            updates=updates
        )

        # Send updates to first layer
        response = await first_layer_node.SyncUpdates(update_group, None)
        assert response.success

        # Verify second layer was notified
        assert first_layer_node.second_layer_stub.SyncUpdates.called
        call_args = first_layer_node.second_layer_stub.SyncUpdates.call_args[0][0]
        assert call_args.source_node == first_layer_node.node_id
        assert call_args.layer == 1
        assert len(call_args.updates) > 0

    async def test_read_consistency_across_layers(
        self, core_node, first_layer_node, second_layer_node
    ):
        """Test read consistency across all layers after updates."""
        # Write data through core node
        write_transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.WRITE, key=1, value=100)
            ]
        )
        write_result = await core_node.ExecuteTransaction(write_transaction, None)
        assert write_result.success

        # Simulate propagation delay
        await asyncio.sleep(0.1)

        # Read from all layers
        read_transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.READ, key=1)
            ]
        )

        # Read from core layer
        core_result = await core_node.ExecuteTransaction(read_transaction, None)
        assert core_result.results[0].value == 100

        # Read from first layer
        first_layer_result = await first_layer_node.ExecuteTransaction(read_transaction, None)
        assert first_layer_result.results[0].value == 100

        # Read from second layer
        second_layer_result = await second_layer_node.ExecuteTransaction(read_transaction, None)
        assert second_layer_result.results[0].value == 100

    async def test_write_rejection_in_non_core_layers(
        self, first_layer_node, second_layer_node
    ):
        """Test that write operations are rejected in non-core layers."""
        # Create a write transaction
        write_transaction = replication_pb2.Transaction(
            operations=[
                replication_pb2.Operation(type=replication_pb2.Operation.WRITE, key=1, value=100)
            ]
        )

        # Attempt write on first layer
        with pytest.raises(Exception, match="Write operations not allowed"):
            await first_layer_node.ExecuteTransaction(write_transaction, None)

        # Attempt write on second layer
        with pytest.raises(Exception, match="Write operations not allowed"):
            await second_layer_node.ExecuteTransaction(write_transaction, None) 