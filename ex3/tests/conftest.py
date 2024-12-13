"""Pytest configuration and shared fixtures"""
import pytest
import asyncio
import logging
from typing import AsyncGenerator
import socket
import time

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def cleanup_ports():
    """Ensure ports are cleaned up after each test"""
    yield
    # Wait for sockets to close properly
    await asyncio.sleep(0.1)

@pytest.fixture
def unused_tcp_port():
    """Find an unused TCP port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

@pytest.fixture
def unused_tcp_port_factory():
    """Create multiple unused TCP ports"""
    def factory():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]
    return factory

@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@pytest.fixture
async def wait_for_port(unused_tcp_port):
    """Wait for a port to become available"""
    async def _wait(port=None, timeout=5):
        port = port or unused_tcp_port
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', port))
                sock.close()
                return True
            except OSError:
                await asyncio.sleep(0.1)
        return False
    return _wait