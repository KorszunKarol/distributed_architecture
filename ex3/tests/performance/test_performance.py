"""Performance tests for distributed mutual exclusion system"""
import pytest
import time
import asyncio
import psutil
import os
from src.algorithms.vector_clock import VectorClock
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig
from src.processes.base_process import BaseProcess

class TestClockPerformance:
    """Performance test cases for Vector Clock"""

    def test_large_process_count(self):
        """Test performance with large number of processes"""
        start_time = time.time()
        process_counts = [10, 100, 1000]

        for count in process_counts:
            # Create clock with many processes
            clock = VectorClock(process_id="0", num_processes=count)

            # Measure memory before operations
            process = psutil.Process(os.getpid())
            mem_before = process.memory_info().rss

            # Perform operations
            clock.increment()
            for i in range(1, count):
                clock.update({str(i): i})

            # Measure memory after operations
            mem_after = process.memory_info().rss
            mem_used = mem_after - mem_before

            # Memory usage should scale linearly with process count
            assert mem_used < count * 1000  # Rough estimate: 1KB per process

        total_time = time.time() - start_time
        assert total_time < 5.0  # Should complete within 5 seconds

    def test_high_frequency_updates(self):
        """Test performance with high frequency updates"""
        clock = VectorClock(process_id="0", num_processes=10)
        updates_per_second = 1000
        duration = 1.0  # 1 second

        start_time = time.time()
        count = 0

        while time.time() - start_time < duration:
            clock.increment()
            count += 1

        actual_rate = count / duration
        assert actual_rate >= updates_per_second * 0.8  # Allow 20% margin

    def test_concurrent_operations(self):
        """Test performance with concurrent operations"""
        num_processes = 10
        operations_per_process = 1000

        async def run_process(process_id: str):
            clock = VectorClock(process_id=process_id, num_processes=num_processes)
            for _ in range(operations_per_process):
                clock.increment()
                await asyncio.sleep(0)  # Allow other coroutines to run
            return clock.get_timestamp()

        async def run_test():
            start_time = time.time()
            tasks = [
                run_process(str(i))
                for i in range(num_processes)
            ]
            results = await asyncio.gather(*tasks)
            end_time = time.time()

            # Verify results
            assert len(results) == num_processes
            for i, result in enumerate(results):
                assert result[str(i)] == operations_per_process

            return end_time - start_time

        total_time = asyncio.run(run_test())
        assert total_time < 5.0  # Should complete within 5 seconds

class TestMessagePerformance:
    """Performance test cases for message handling"""

    @pytest.mark.asyncio
    async def test_message_throughput(self):
        """Test message throughput"""
        # Create server and client
        server = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )
        client = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="B")
        )

        # Start server
        server.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Parameters
        num_messages = 1000
        message_size = 1024  # 1KB
        start_time = time.time()

        # Send messages
        data = "x" * message_size
        send_tasks = [
            client.send_message(
                Message(
                    msg_type=MessageType.REQUEST,
                    sender_id="TEST1",
                    timestamp=i,
                    data=data
                ),
                NetworkConfig.TEST_PORT
            ) for i in range(num_messages)
        ]

        # Receive messages
        receive_tasks = [
            server.receive_message()
            for _ in range(num_messages)
        ]

        # Wait for all operations to complete
        await asyncio.gather(
            *send_tasks,
            *receive_tasks
        )

        # Calculate throughput
        total_time = time.time() - start_time
        throughput = num_messages / total_time
        assert throughput >= 100  # At least 100 messages per second

    @pytest.mark.asyncio
    async def test_message_latency(self):
        """Test message latency"""
        # Create server and client
        server = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )
        client = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="B")
        )

        # Start server
        server.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Measure round-trip time
        start_time = time.time()

        # Send message
        await client.send_message(
            Message(
                msg_type=MessageType.REQUEST,
                sender_id="TEST1",
                timestamp=0
            ),
            NetworkConfig.TEST_PORT
        )

        # Receive message
        await server.receive_message()

        # Calculate latency
        latency = time.time() - start_time
        assert latency < 0.1  # Less than 100ms

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage under load"""
        # Create server and client
        server = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )
        client = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="B")
        )

        # Start server
        server.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Parameters
        num_messages = 1000
        message_size = 1024 * 1024  # 1MB

        # Measure initial memory
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss

        # Send and receive messages
        data = "x" * message_size
        for i in range(num_messages):
            await client.send_message(
                Message(
                    msg_type=MessageType.REQUEST,
                    sender_id="TEST1",
                    timestamp=i,
                    data=data
                ),
                NetworkConfig.TEST_PORT
            )
            await server.receive_message()

        # Measure final memory
        mem_after = process.memory_info().rss
        mem_per_message = (mem_after - mem_before) / num_messages

        # Memory usage should be reasonable
        assert mem_per_message < message_size * 2  # Allow for some overhead