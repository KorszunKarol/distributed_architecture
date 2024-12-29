import pytest
import asyncio
import grpc
from datetime import datetime
from src.node.core_node import CoreNode
from src.node.second_layer import SecondLayerNode
from src.proto import replication_pb2, replication_pb2_grpc

@pytest.fixture
async def nodes():
    core_ports = [50061, 50062]
    core_addresses = [f'localhost:{port}' for port in core_ports]
    second_layer_port = 50063

    core_nodes = []
    for i, port in enumerate(core_ports):
        node = CoreNode(
            node_id=f"core_{i}",
            log_dir="test_logs",
            port=port,
            peer_addresses=[addr for addr in core_addresses if addr != f'localhost:{port}']
        )
        await node.start()
        core_nodes.append(node)

    second_layer = SecondLayerNode(
        node_id="second_1",
        log_dir="test_logs",
        port=second_layer_port,
        core_addresses=core_addresses,
        primary_core=core_addresses[0]
    )
    await second_layer.start()

    return (core_nodes, second_layer)

@pytest.mark.asyncio
async def test_lazy_replication(nodes):
    core_nodes, second_layer = await anext(nodes)
    channel = grpc.aio.insecure_channel(f'localhost:{core_nodes[0].port}')
    stub = replication_pb2_grpc.NodeServiceStub(channel)

    for i in range(15):
        transaction = replication_pb2.Transaction(
            type=replication_pb2.Transaction.UPDATE,
            operations=[
                replication_pb2.Operation(
                    type=replication_pb2.Operation.WRITE,
                    key=i,
                    value=i * 100
                )
            ]
        )
        response = await stub.ExecuteTransaction(transaction)
        assert response.success

    await asyncio.sleep(2)

    second_status = await second_layer.GetNodeStatus(replication_pb2.Empty())
    assert len(second_status.current_data) == 15
    for i in range(15):
        assert any(item.key == i and item.value == i * 100 for item in second_status.current_data)