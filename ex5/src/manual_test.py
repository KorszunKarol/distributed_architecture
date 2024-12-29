import asyncio
import grpc
import aiohttp
from datetime import datetime
import pathlib
import time

from node.core_node import CoreNode
from node.second_layer import SecondLayerNode
from node.third_layer import ThirdLayerNode
from proto import replication_pb2, replication_pb2_grpc
from transaction.parser import TransactionParser

async def setup_nodes():
    core_ports = [50051, 50052, 50053]  # A1, A2, A3
    core_addresses = [f'localhost:{port}' for port in core_ports]
    core_nodes = []

    for i, port in enumerate(core_ports):
        node = CoreNode(
            node_id=f"A{i+1}",  # A1, A2, A3
            log_dir="test_logs",
            port=port,
            peer_addresses=[addr for addr in core_addresses if addr != f'localhost:{port}']
        )
        await node.start()
        core_nodes.append(node)

    second_layer_nodes = []
    for i, port in enumerate([50054, 50055]):  # B1, B2
        node = SecondLayerNode(
            node_id=f"B{i+1}",
            log_dir="test_logs",
            port=port,
            core_addresses=core_addresses,
            primary_core=core_addresses[0]
        )
        await node.start()
        second_layer_nodes.append(node)

    third_layer_nodes = []
    for i, port in enumerate([50056, 50057]):  # C1, C2
        node = ThirdLayerNode(
            node_id=f"C{i+1}",
            log_dir="test_logs",
            port=port,
            core_addresses=core_addresses,
            primary_core=core_addresses[0]
        )
        await node.start()
        third_layer_nodes.append(node)

    return core_nodes, second_layer_nodes, third_layer_nodes

async def cleanup_nodes(core_nodes, second_layer_nodes, third_layer_nodes):
    tasks = []
    for node in second_layer_nodes + third_layer_nodes + core_nodes:
        if hasattr(node, 'server') and node.server:
            tasks.append(node.server.stop(grace=1))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def send_node_status(node, session):
    try:
        status = await node.GetNodeStatus(replication_pb2.Empty())
        state = {
            "node_id": status.node_id,
            "layer": status.layer,
            "update_count": status.update_count,
            "current_data": [
                {
                    "key": item.key,
                    "value": item.value,
                    "version": item.version,
                    "timestamp": item.timestamp
                }
                for item in status.current_data
            ],
            "last_update": time.time()
        }
        print(f"Sending state for {status.node_id}:", state)  
        async with session.post(f"http://localhost:8000/node/{status.node_id}/state", json=state) as response:
            print(f"Response for {status.node_id}:", await response.json())
    except Exception as e:
        print(f"Error sending status for {node.node_id}: {e}")

async def monitor_nodes(core_nodes, second_layer_nodes, third_layer_nodes):
    async with aiohttp.ClientSession() as session:
        while True:
            for node in core_nodes + second_layer_nodes + third_layer_nodes:
                try:
                    await send_node_status(node, session)
                except Exception as e:
                    print(f"Error sending status for {node.node_id}: {e}")
            await asyncio.sleep(1)

async def test_transactions(core_nodes, second_layer_nodes, third_layer_nodes):
    parser = TransactionParser()

    transactions = [
        "b0, r(1), r(2), c",
        "b, r(1), w(2,200), c",
        "b1, r(2), r(3), c",
        "b2, r(1), r(2), c",
    ]

    channel = grpc.aio.insecure_channel(f'localhost:{core_nodes[0].port}')
    stub = replication_pb2_grpc.NodeServiceStub(channel)

    for tx_str in transactions:
        try:
            transaction = parser.parse_transaction(tx_str)
            parser.validate_transaction(transaction)

            print(f"\nExecuting transaction: {tx_str}")
            response = await stub.ExecuteTransaction(transaction)
            print(f"Response: {response}")

            await asyncio.sleep(2)

        except Exception as e:
            print(f"Error processing transaction '{tx_str}': {e}")

async def test_replication():
    core_nodes, second_layer_nodes, third_layer_nodes = await setup_nodes()
    monitor_task = None
    channel = None

    try:
        monitor_task = asyncio.create_task(
            monitor_nodes(core_nodes, second_layer_nodes, third_layer_nodes)
        )

        await test_transactions(core_nodes, second_layer_nodes, third_layer_nodes)
        await asyncio.sleep(15)

    finally:
        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        await cleanup_nodes(core_nodes, second_layer_nodes, third_layer_nodes)

        if channel:
            await channel.close()

if __name__ == "__main__":
    try:
        asyncio.run(test_replication())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")