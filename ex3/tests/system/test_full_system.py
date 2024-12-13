"""System tests for distributed mutual exclusion system"""
import pytest
import asyncio
import time
import signal
import subprocess
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig
from src.processes.base_process import BaseProcess
from src.processes.heavyweight_a import ProcessA
from src.processes.heavyweight_b import ProcessB
from src.processes.lightweight_a import LightweightProcessA
from src.processes.lightweight_b import LightweightProcessB

class TestFullSystem:
    """System test cases for the complete distributed system"""

    @pytest.mark.asyncio
    async def test_mutual_exclusion_cycle(self):
        """Test complete mutual exclusion cycle"""
        # Create heavyweight processes
        process_a = ProcessA()
        process_b = ProcessB()

        # Create lightweight processes
        lightweight_a = [
            LightweightProcessA(number=i)
            for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES)
        ]
        lightweight_b = [
            LightweightProcessB(number=i)
            for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES)
        ]

        # Start all processes
        process_a.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        process_b.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        for process in lightweight_a + lightweight_b:
            process.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Run mutual exclusion cycle
        try:
            # Trigger critical section requests
            for process in lightweight_a:
                await process.request_cs()
            for process in lightweight_b:
                await process.request_cs()

            # Allow time for token passing
            await asyncio.sleep(1)

            # Release critical sections
            for process in lightweight_a:
                await process.release_cs()
            for process in lightweight_b:
                await process.release_cs()

        finally:
            # Cleanup
            process_a.cleanup()
            process_b.cleanup()
            for process in lightweight_a + lightweight_b:
                process.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of multiple concurrent requests"""
        # Create processes
        process_a = ProcessA()
        process_b = ProcessB()
        lightweight_processes = [
            LightweightProcessA(number=i)
            for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES)
        ]

        # Start processes
        process_a.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        process_b.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        for process in lightweight_processes:
            process.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        try:
            # Send concurrent requests
            await asyncio.gather(*[
                process.request_cs()
                for process in lightweight_processes
            ])

            # Allow time for processing
            await asyncio.sleep(1)

            # Release critical sections
            await asyncio.gather(*[
                process.release_cs()
                for process in lightweight_processes
            ])

        finally:
            # Cleanup
            process_a.cleanup()
            process_b.cleanup()
            for process in lightweight_processes:
                process.cleanup()

    @pytest.mark.asyncio
    async def test_system_recovery(self):
        """Test system recovery after failures"""
        # Create processes
        process_a = ProcessA()
        process_b = ProcessB()
        lightweight_a = LightweightProcessA(number=1)
        lightweight_b = LightweightProcessB(number=1)

        # Start processes
        process_a.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        process_b.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        lightweight_a.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        lightweight_b.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        try:
            # Start normal operation
            await lightweight_a.request_cs()
            await lightweight_b.request_cs()

            # Simulate process failure
            process_a.cleanup()
            await asyncio.sleep(1)

            # Restart failed process
            process_a = ProcessA()
            process_a.socket.listen(NetworkConfig.SOCKET_BACKLOG)
            await asyncio.sleep(1)

            # System should recover
            await lightweight_a.release_cs()
            await lightweight_b.release_cs()

        finally:
            # Cleanup
            process_a.cleanup()
            process_b.cleanup()
            lightweight_a.cleanup()
            lightweight_b.cleanup()

    @pytest.mark.asyncio
    async def test_process_crashes(self):
        """Test handling of process crashes and restarts"""
        # Start processes using subprocess
        processes = []
        try:
            # Start heavyweight processes
            process_a = subprocess.Popen(["python", "-m", "src.processes.heavyweight_a"])
            process_b = subprocess.Popen(["python", "-m", "src.processes.heavyweight_b"])
            processes.extend([process_a, process_b])

            # Allow processes to start
            await asyncio.sleep(1)

            # Simulate crash by terminating process_a
            process_a.terminate()
            process_a.wait()
            processes.remove(process_a)

            # Wait for system to detect failure
            await asyncio.sleep(1)

            # Restart process_a
            process_a = subprocess.Popen(["python", "-m", "src.processes.heavyweight_a"])
            processes.append(process_a)

            # Allow system to recover
            await asyncio.sleep(1)

            # Verify processes are running
            for process in processes:
                assert process.poll() is None

        finally:
            # Cleanup
            for process in processes:
                process.terminate()
                process.wait()

    @pytest.mark.asyncio
    async def test_token_passing(self):
        """Test token passing between heavyweight processes"""
        # Create processes
        process_a = ProcessA()  # Starts with token
        process_b = ProcessB()  # Starts without token

        # Start processes
        process_a.socket.listen(NetworkConfig.SOCKET_BACKLOG)
        process_b.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        try:
            # Verify initial token state
            assert process_a.has_token == True
            assert process_b.has_token == False

            # Trigger token passing
            await process_b.request_token()
            await asyncio.sleep(1)

            # Verify token has passed
            assert process_a.has_token == False
            assert process_b.has_token == True

            # Pass token back
            await process_a.request_token()
            await asyncio.sleep(1)

            # Verify token returned
            assert process_a.has_token == True
            assert process_b.has_token == False

        finally:
            # Cleanup
            process_a.cleanup()
            process_b.cleanup()