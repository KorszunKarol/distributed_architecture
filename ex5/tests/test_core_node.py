import pytest
import asyncio
import grpc
from datetime import datetime
from src.node.core_node import CoreNode
from src.proto import replication_pb2, replication_pb2_grpc

@pytest.fixture
async def core_nodes():
    nodes = []
    ports = [50051, 50052, 50053]
    addresses = [f'localhost:{port}' for port in ports]

    for i, port in enumerate(ports):
        node = CoreNode(
            node_id=f"core_{i}",
            log_dir="test_logs",
            port=port,
            peer_addresses=[addr for addr in addresses if addr != f'localhost:{port}']
        )
        await node.start()
        nodes.append(node)

    yield nodes

@pytest.mark.asyncio
async def test_eager_replication(core_nodes):
    nodes = await anext(core_nodes)
    channel = grpc.aio.insecure_channel(f'localhost:{nodes[0].port}')
    stub = replication_pb2_grpc.NodeServiceStub(channel)

    transaction = replication_pb2.Transaction(
        type=replication_pb2.Transaction.UPDATE,
        operations=[
            replication_pb2.Operation(
                type=replication_pb2.Operation.WRITE,
                key=1,
                value=100
            )
        ]
    )

    response = await stub.ExecuteTransaction(transaction)
    assert response.success

    for node in nodes:
        status = await node.GetNodeStatus(replication_pb2.Empty())
        assert len(status.current_data) == 1
        assert status.current_data[0].key == 1
        assert status.current_data[0].value == 100
        assert status.current_data[0].version == 1

@pytest.mark.asyncio
async def test_concurrent_updates(core_nodes):
    nodes = await anext(core_nodes)
    channels = [
        grpc.aio.insecure_channel(f'localhost:{node.port}')
        for node in nodes
    ]
    stubs = [replication_pb2_grpc.NodeServiceStub(channel) for channel in channels]

    transactions = []
    for i, stub in enumerate(stubs):
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
        transactions.append(stub.ExecuteTransaction(transaction))

    responses = await asyncio.gather(*transactions)
    assert all(r.success for r in responses)

    for node in nodes:
        status = await node.GetNodeStatus(replication_pb2.Empty())
        assert len(status.current_data) == len(nodes)
        for i in range(len(nodes)):
            assert any(item.key == i and item.value == i * 100 for item in status.current_data)