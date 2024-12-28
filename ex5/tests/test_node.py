import pytest
import asyncio
import grpc
from datetime import datetime
from src.node.base_node import BaseNode
from src.proto import replication_pb2
from src.proto import replication_pb2_grpc



@pytest.fixture
async def node():
    node = BaseNode("test_node", 0, "test_logs", 50051)
    await node.start()
    yield node
    await node.stop()

@pytest.fixture
async def channel():
    channel = grpc.aio.insecure_channel('localhost:50051')
    yield channel
    await channel.close()

@pytest.mark.asyncio
async def test_propagate_update(node, channel):
    node = await anext(node)
    channel = await anext(channel)

    stub = replication_pb2_grpc.NodeServiceStub(channel)

    request = replication_pb2.UpdateNotification(
        data=replication_pb2.DataItem(
            key=1,
            value=100,
            version=1,
            timestamp=int(datetime.now().timestamp())
        ),
        source_node="test_source"
    )

    response = await stub.PropagateUpdate(request)
    assert response.success

    status = await stub.GetNodeStatus(replication_pb2.Empty())
    assert len(status.current_data) == 1
    assert status.current_data[0].key == 1
    assert status.current_data[0].value == 100