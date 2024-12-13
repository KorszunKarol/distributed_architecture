"""Network tests for distributed mutual exclusion system"""
import pytest
import asyncio
import socket
from contextlib import asynccontextmanager
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig
from src.processes.base_process import BaseProcess

@asynccontextmanager
async def create_test_process(process_type="TEST", group="A", port=None):
    """Async context manager for test process creation and cleanup"""
    process = BaseProcess(
        process_id=ProcessId(process_type=process_type, group=group),
        port=port or NetworkConfig.TEST_PORT
    )
    try:
        yield process
    finally:
        if hasattr(process, 'socket') and process.socket:
            process.socket.close()

class TestNetworkFailures:
    """Test cases for network failures"""

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test handling of connection timeouts"""
        async with create_test_process() as process:
            # Try to send message to non-existent port
            with pytest.raises(ConnectionRefusedError):
                await process.send_message(
                    Message(
                        msg_type=MessageType.REQUEST,
                        sender_id="TEST1",
                        timestamp=0
                    ),
                    NetworkConfig.TEST_PORT + 1
                )

    @pytest.mark.asyncio
    async def test_message_corruption(self):
        """Test handling of corrupted messages"""
        async with create_test_process(port=NetworkConfig.TEST_PORT) as server:
            async with create_test_process(group="B") as client:
                # Start server
                server.socket.listen(NetworkConfig.SOCKET_BACKLOG)

                # Send corrupted message using context manager
                async with await asyncio.open_connection(NetworkConfig.HOST, NetworkConfig.TEST_PORT) as (reader, writer):
                    try:
                        writer.write(b"corrupted data")
                        await writer.drain()
                    finally:
                        writer.close()
                        await writer.wait_closed()

    @pytest.mark.asyncio
    async def test_message_ordering(self):
        """Test handling of message ordering"""
        # Create server and client processes
        server = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )
        client = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="B")
        )

        # Start server
        server.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Send messages in order
        messages = [
            Message(
                msg_type=MessageType.REQUEST,
                sender_id="TEST1",
                timestamp=i
            ) for i in range(3)
        ]

        # Send messages concurrently
        await asyncio.gather(*[
            client.send_message(msg, NetworkConfig.TEST_PORT)
            for msg in messages
        ])

        # Receive messages
        received = []
        for _ in range(3):
            msg = await server.receive_message()
            received.append(msg)

        # Messages might arrive in different order
        assert len(received) == 3
        assert all(msg.msg_type == MessageType.REQUEST for msg in received)
        assert all(msg.sender_id == "TEST1" for msg in received)
        assert sorted(msg.timestamp for msg in received) == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test handling of concurrent connections"""
        # Create server and multiple client processes
        server = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )
        clients = [
            BaseProcess(
                process_id=ProcessId(process_type="TEST", group="B", number=i)
            ) for i in range(3)
        ]

        # Start server
        server.socket.listen(NetworkConfig.SOCKET_BACKLOG)

        # Send messages from all clients concurrently
        await asyncio.gather(*[
            client.send_message(
                Message(
                    msg_type=MessageType.REQUEST,
                    sender_id=f"TEST{i}",
                    timestamp=i
                ),
                NetworkConfig.TEST_PORT
            ) for i, client in enumerate(clients)
        ])

        # Receive all messages
        received = []
        for _ in range(3):
            msg = await server.receive_message()
            received.append(msg)

        # Verify all messages were received
        assert len(received) == 3
        assert all(msg.msg_type == MessageType.REQUEST for msg in received)
        assert sorted(msg.sender_id for msg in received) == ["TEST0", "TEST1", "TEST2"]
        assert sorted(msg.timestamp for msg in received) == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_socket_cleanup(self):
        """Test proper socket cleanup"""
        process = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )

        # Cleanup should close the socket
        process.cleanup()

        # Socket should be closed
        assert process.socket._closed

        # Creating new process with same port should succeed
        new_process = BaseProcess(
            process_id=ProcessId(process_type="TEST", group="A"),
            port=NetworkConfig.TEST_PORT
        )
        assert not new_process.socket._closed