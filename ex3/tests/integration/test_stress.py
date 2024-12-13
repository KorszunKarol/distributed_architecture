"""Stress tests for distributed mutual exclusion system"""
import pytest
import asyncio
import time
import psutil
import os
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig
from src.processes.base_process import BaseProcess
from src.processes.lightweight_a import LightweightProcessA
from src.processes.lightweight_b import LightweightProcessB

class TestSystemStress:
    """Stress test cases for the distributed system"""

    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test system under sustained high load"""
        # Create processes
        num_processes = 10
        processes = []
        ports = []

        # Create and start processes
        for i in range(num_processes):
            port = NetworkConfig.TEST_PORT + i
            process = BaseProcess(
                process_id=ProcessId(process_type="TEST", group="A", number=i),
                port=port
            )
            process.socket.listen(NetworkConfig.SOCKET_BACKLOG)
            processes.append(process)
            ports.append(port)

        # Run for specified duration
        duration = 10  # seconds
        message_count = 0
        start_time = time.time()

        while time.time() - start_time < duration:
            # Each process sends a message to every other process
            tasks = []
            for i, sender in enumerate(processes):
                for j, port in enumerate(ports):
                    if i != j:
                        tasks.append(
                            sender.send_message(
                                Message(
                                    msg_type=MessageType.REQUEST,
                                    sender_id=f"TEST{i}",
                                    timestamp=message_count
                                ),
                                port
                            )
                        )

            # Send messages concurrently
            await asyncio.gather(*tasks)
            message_count += 1

            # Allow system to process messages
            await asyncio.sleep(0.1)

        # Cleanup
        for process in processes:
            process.cleanup()

        # Verify system remained responsive
        messages_per_second = message_count * num_processes * (num_processes - 1) / duration
        assert messages_per_second > 100  # At least 100 messages per second

    @pytest.mark.asyncio
    async def test_resource_exhaustion(self):
        """Test system behavior under resource exhaustion"""
        # Create processes with large message sizes
        server = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )
        client = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="B")
        )

        # Start server
        server.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Monitor system resources
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        max_memory_increase = 1024 * 1024 * 1024  # 1GB

        # Send increasingly large messages
        message_size = 1024  # Start with 1KB
        while process.memory_info().rss - initial_memory < max_memory_increase:
            data = "x" * message_size

            # Send and receive message
            await client.send_message(
                Message(
                    msg_type=MessageType.REQUEST,
                    sender_id="TEST1",
                    timestamp=0,
                    data=data
                ),
                NetworkConfig.TEST_PORT
            )
            await server.receive_message()

            message_size *= 2

        # Cleanup
        server.cleanup()
        client.cleanup()

    @pytest.mark.asyncio
    async def test_long_running_operations(self):
        """Test system stability during long-running operations"""
        # Create processes
        process_a = LightweightProcessA(
            number=1,
            port=NetworkConfig.TEST_PORT
        )
        process_b = LightweightProcessB(
            number=1,
            port=NetworkConfig.TEST_PORT + 1
        )

        # Start processes
        process_a.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        process_b.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Run operations for extended period
        duration = 30  # seconds
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < duration:
            # Request critical section
            await process_a.request_cs()
            await process_b.request_cs()

            # Release critical section
            await process_a.release_cs()
            await process_b.release_cs()

            operation_count += 1

        # Verify system remained stable
        assert operation_count > 0
        operations_per_second = operation_count / duration
        assert operations_per_second > 1  # At least 1 complete operation per second

        # Cleanup
        process_a.cleanup()
        process_b.cleanup()

    @pytest.mark.asyncio
    async def test_process_churn(self):
        """Test system under continuous process creation/deletion"""
        active_processes = []
        active_ports = set()
        base_port = NetworkConfig.TEST_PORT
        max_processes = 50
        operations_per_cycle = 10

        async def create_process():
            """Create a new process"""
            # Find available port
            port = base_port
            while port in active_ports:
                port += 1
            active_ports.add(port)

            # Create process
            process = BaseProcess(
                process_id=ProcessId(process_type="TEST", group="A", number=len(active_processes)),
                port=port
            )
            process.socket.listen(NetworkConfig.SOCKET_BACKLOG)
            active_processes.append((process, port))
            return process, port

        async def delete_process():
            """Delete a random process"""
            if active_processes:
                process, port = active_processes.pop()
                active_ports.remove(port)
                process.cleanup()

        # Run for specified duration
        duration = 20  # seconds
        start_time = time.time()

        while time.time() - start_time < duration:
            # Create new processes
            while len(active_processes) < max_processes:
                await create_process()

            # Perform operations
            for _ in range(operations_per_cycle):
                if len(active_processes) >= 2:
                    sender, _ = active_processes[0]
                    _, receiver_port = active_processes[1]
                    await sender.send_message(
                        Message(
                            msg_type=MessageType.REQUEST,
                            sender_id="TEST1",
                            timestamp=0
                        ),
                        receiver_port
                    )

            # Delete some processes
            for _ in range(max_processes // 4):
                await delete_process()

            # Allow system to stabilize
            await asyncio.sleep(0.1)

        # Cleanup remaining processes
        while active_processes:
            await delete_process()