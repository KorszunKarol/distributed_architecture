"""Network and process configuration constants for the distributed mutual exclusion system.

This module defines configuration constants used throughout the distributed mutual
exclusion system, including network settings, process settings, and message formats.
"""
from dataclasses import dataclass
from enum import Enum

class ProcessGroup(Enum):
    """Process group identifiers.

    Attributes:
        A: Group A processes.
        B: Group B processes.
    """
    A = "A"
    B = "B"

class ProcessType(Enum):
    """Process type identifiers.

    Attributes:
        HEAVY: Heavyweight process type.
        LIGHT: Lightweight process type.
    """
    HEAVY = "HEAVY"
    LIGHT = "LIGHT"

@dataclass(frozen=True)
class NetworkConfig:
    """Network configuration settings.

    Attributes:
        HOST: Host address for all processes (127.0.0.1).
        SOCKET_BACKLOG: Maximum length of the socket backlog queue.
        BUFFER_SIZE: Size of socket receive buffer in bytes.
        MAX_RETRIES: Maximum number of retry attempts for operations.
        RETRY_DELAY: Delay between retry attempts in seconds.
        MESSAGE_TIMEOUT: Timeout for message operations in seconds.
        HEARTBEAT_INTERVAL: Interval between heartbeat messages in seconds.
        MONITOR_INTERVAL: Interval for connection monitoring in seconds.
        TOKEN_TIMEOUT: Timeout for token passing operations in seconds.
        BASE_PORT: Base port number for all processes.
        HEAVYWEIGHT_A_PORT: Port for heavyweight process A.
        HEAVYWEIGHT_B_PORT: Port for heavyweight process B.
        LIGHTWEIGHT_BASE_PORT: Base port for lightweight processes.
        LIGHTWEIGHT_A_BASE_PORT: Base port for group A lightweight processes.
        LIGHTWEIGHT_B_BASE_PORT: Base port for group B lightweight processes.
        NUM_LIGHTWEIGHT_PROCESSES: Number of lightweight processes per group.
    """
    # Network settings
    HOST = "127.0.0.1"
    SOCKET_BACKLOG = 10
    BUFFER_SIZE = 4096
    MAX_RETRIES = 3
    RETRY_DELAY = 0.1
    MESSAGE_TIMEOUT = 2.0
    HEARTBEAT_INTERVAL = 1.0
    MONITOR_INTERVAL = 2.0
    TOKEN_TIMEOUT = 5.0

    # Port configuration
    BASE_PORT = 5000
    HEAVYWEIGHT_A_PORT = BASE_PORT
    HEAVYWEIGHT_B_PORT = BASE_PORT + 1
    LIGHTWEIGHT_BASE_PORT = BASE_PORT + 2
    LIGHTWEIGHT_A_BASE_PORT = LIGHTWEIGHT_BASE_PORT
    LIGHTWEIGHT_B_BASE_PORT = LIGHTWEIGHT_BASE_PORT + 3
    NUM_LIGHTWEIGHT_PROCESSES = 3

@dataclass(frozen=True)
class ProcessConfig:
    """Process configuration settings.

    Attributes:
        DISPLAY_TIME: Time between display messages in seconds.
        DISPLAY_COUNT: Number of times each process displays its ID.
        PROCESS_STARTUP_DELAY: Delay between process startups in seconds.
        CLEANUP_TIMEOUT: Timeout for process cleanup operations in seconds.
    """
    DISPLAY_TIME = 1.0
    DISPLAY_COUNT = 10
    PROCESS_STARTUP_DELAY = 0.1
    CLEANUP_TIMEOUT = 2.0

@dataclass(frozen=True)
class MessageConfig:
    """Message format configuration.

    Attributes:
        ID_FORMAT_HEAVY: Format string for heavyweight process IDs.
        ID_FORMAT_LIGHT: Format string for lightweight process IDs.
        DISPLAY_FORMAT: Format string for process display messages.
        MAX_MESSAGE_SIZE: Maximum size of a message in bytes.
    """
    ID_FORMAT_HEAVY = "HW{}"
    ID_FORMAT_LIGHT = "LW{}{}"
    DISPLAY_FORMAT = "I'm lightweight process {}{}"
    MAX_MESSAGE_SIZE = NetworkConfig.BUFFER_SIZE - 1024

@dataclass(frozen=True)
class TestConfig:
    """Test configuration settings.

    Attributes:
        TEST_PORT: Port number used for testing.
        TEST_TIMEOUT: Timeout for test operations in seconds.
        TEST_STARTUP_DELAY: Delay between test startups in seconds.
    """
    TEST_PORT: int = 8000
    TEST_TIMEOUT: float = 2.0
    TEST_STARTUP_DELAY: float = 0.1