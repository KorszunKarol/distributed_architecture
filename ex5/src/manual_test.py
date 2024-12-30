"""Manual test script for the distributed system."""
import asyncio
import os
import grpc
import logging
from datetime import datetime
from src.node.core_node import CoreNode
from src.node.second_layer import SecondLayerNode
from src.node.third_layer import ThirdLayerNode
from src.proto import replication_pb2, replication_pb2_grpc
from web.backend.monitor import NodeMonitor, NodeState
from src.transaction.processor import TransactionProcessor

class TestSystem:
    def __init__(self, enable_file_logging=False):
        """
        Initialize test system with all layers and logging configuration.

        Args:
            enable_file_logging (bool): If True, logs will be saved to a file in addition to console output.
        """
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        self.monitor = NodeMonitor()

        if enable_file_logging:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_dir, f"test_run_{timestamp}.log")
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )

        self.core_addresses = [
            'localhost:50051',
            'localhost:50052',
            'localhost:50053'
        ]
        self.core_nodes = []

        self.second_layer_addresses = [
            'localhost:50054',
            'localhost:50055'
        ]
        self.second_layer_nodes = []

        self.third_layer_addresses = [
            'localhost:50056',
            'localhost:50057'
        ]
        self.third_layer_nodes = []

    async def setup_nodes(self):
        """Set up all nodes in the system across all layers."""
        logging.info("Setting up core layer...")
        for i, addr in enumerate(self.core_addresses):
            port = int(addr.split(':')[1])
            logging.info(f"Starting core node A{i+1} on port {port}")
            node = CoreNode(
                node_id=f'A{i+1}',
                log_dir=self.log_dir,
                port=port,
                peer_addresses=[a for a in self.core_addresses if a != addr]
            )
            await node.start()
            self.core_nodes.append(node)
            logging.info(f"Core node A{i+1} started")

        logging.info("Setting up second layer...")
        for i, addr in enumerate(self.second_layer_addresses):
            port = int(addr.split(':')[1])
            is_primary = (i == 0)
            role = "primary" if is_primary else "backup"
            logging.info(f"Starting second layer node B{i+1} ({role}) on port {port}")
            node = SecondLayerNode(
                node_id=f'B{i+1}',
                log_dir=self.log_dir,
                port=port,
                primary_core_address=self.core_addresses[0],
                is_primary=is_primary,
                backup_addresses=self.second_layer_addresses
            )
            await node.start()
            self.second_layer_nodes.append(node)
            logging.info(f"Second layer node B{i+1} started")

        logging.info("Setting up third layer...")
        for i, addr in enumerate(self.third_layer_addresses):
            port = int(addr.split(':')[1])
            is_primary = (i == 0)
            role = "primary" if is_primary else "backup"
            logging.info(f"Starting third layer node C{i+1} ({role}) on port {port}")
            node = ThirdLayerNode(
                node_id=f'C{i+1}',
                log_dir=self.log_dir,
                port=port,
                primary_core_address=self.core_addresses[0],
                is_primary=is_primary,
                backup_addresses=self.third_layer_addresses
            )
            await node.start()
            self.third_layer_nodes.append(node)
            logging.info(f"Third layer node C{i+1} started")

    async def update_monitor(self):
        """Update monitor with current node states continuously."""
        while True:
            try:
                for node in self.core_nodes:
                    context = grpc.aio.ServicerContext(None)
                    status = await node.GetNodeStatus(replication_pb2.Empty(), context)
                    state = NodeState(
                        node_id=node.node_id,
                        layer=0,
                        update_count=len(status.current_data),
                        current_data=[{
                            'key': item.key,
                            'value': item.value,
                            'version': item.version,
                            'timestamp': item.timestamp
                        } for item in status.current_data],
                        last_sync_time=0,
                        last_sync_count=0,
                        operation_log=[]
                    )
                    await self.monitor.update_node_state(node.node_id, state)

                for node in self.second_layer_nodes:
                    context = grpc.aio.ServicerContext(None)
                    status = await node.GetNodeStatus(replication_pb2.Empty(), context)
                    state = NodeState(
                        node_id=node.node_id,
                        layer=1,
                        update_count=len(status.current_data),
                        current_data=[{
                            'key': item.key,
                            'value': item.value,
                            'version': item.version,
                            'timestamp': item.timestamp
                        } for item in status.current_data],
                        last_sync_time=0,
                        last_sync_count=getattr(node, 'last_update_count', 0),
                        operation_log=[]
                    )
                    await self.monitor.update_node_state(node.node_id, state)

                for node in self.third_layer_nodes:
                    context = grpc.aio.ServicerContext(None)
                    status = await node.GetNodeStatus(replication_pb2.Empty(), context)
                    state = NodeState(
                        node_id=node.node_id,
                        layer=2,
                        update_count=len(status.current_data),
                        current_data=[{
                            'key': item.key,
                            'value': item.value,
                            'version': item.version,
                            'timestamp': item.timestamp
                        } for item in status.current_data],
                        last_sync_time=getattr(node, 'last_sync_time', 0),
                        last_sync_count=0,
                        operation_log=[]
                    )
                    await self.monitor.update_node_state(node.node_id, state)

            except Exception as e:
                logging.error(f"Error updating monitor: {e}")

            await asyncio.sleep(1)

    async def run_test(self):
        """Execute test scenarios and monitor system behavior."""
        logging.info("Starting nodes...")
        channel = None
        monitor_task = None
        processor = TransactionProcessor()

        try:
            await self.setup_nodes()
            logging.info("All nodes started successfully")

            monitor_task = asyncio.create_task(self.update_monitor())

            logging.info("Executing test transactions...")
            test_transactions = [
                "b0,r(1),r(2),c",
                "b,w(1,100),w(2,200),c",
                "b1,r(1),r(2),c",
                "b2,r(1),r(2),c",
                "b,w(3,300),w(4,400),c"
            ]

            channel = grpc.aio.insecure_channel(self.core_addresses[0])
            stub = replication_pb2_grpc.NodeServiceStub(channel)

            for tx_str in test_transactions:
                logging.info(f"Executing: {tx_str}")
                try:
                    parsed_tx = processor.parse_transaction(tx_str)
                    grpc_tx = processor.create_grpc_transaction(parsed_tx)
                    response = await stub.ExecuteTransaction(grpc_tx)
                    logging.info(f"Response: {response}")
                except ValueError as e:
                    logging.error(f"Transaction parsing failed: {e}")
                except Exception as e:
                    logging.error(f"Transaction execution failed: {e}")

                await asyncio.sleep(2)

            logging.info("Waiting to observe replication...")
            await asyncio.sleep(15)
            logging.info("Test completed")

        except Exception as e:
            logging.error(f"Error during test: {e}")
            raise
        finally:
            if monitor_task:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            if channel:
                await channel.close()
            await self.cleanup()

    async def cleanup(self):
        """Clean up and stop all nodes."""
        for node in self.core_nodes:
            await node.stop()
        for node in self.second_layer_nodes:
            await node.stop()
        for node in self.third_layer_nodes:
            await node.stop()

async def main():
    """Execute the main test sequence."""
    test_system = TestSystem(enable_file_logging=True)
    await test_system.run_test()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")