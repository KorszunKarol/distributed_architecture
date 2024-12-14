"""Base lightweight process implementation for distributed mutual exclusion."""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig, ProcessConfig
from src.processes.base_process import BaseProcess

@dataclass
class LightweightProcess(BaseProcess):
    """Base class for lightweight processes.

    Provides common functionality for critical section management and coordination
    with heavyweight processes.

    Attributes:
        process_id: Process identifier object
        port: Network port for communication
        number: Process number within group
    """
    number: int = field(init=False)  # Will be set in __init__
    _line_number: int = field(default=1, init=False)
    _process_id_obj: ProcessId = field(init=False)

    def __init__(self, group: str, number: int, port: int):
        """Initialize lightweight process.

        Args:
            group: Process group (A or B)
            number: Process number within group
            port: Network port for communication
        """
        # Create ProcessId first
        self._process_id_obj = ProcessId(
            process_type="LIGHT",
            group=group,
            number=number
        )

        # Initialize base class with string representation for logging
        super().__init__(process_id=str(self._process_id_obj), port=port)

        # Store number
        self.number = number

    def get_process_id(self) -> str:
        """Get formatted process ID."""
        return f"LW{self._process_id_obj.group}{self.number + 1}"

    async def wait_heavyweight(self) -> None:
        """Wait for signal from heavyweight process while handling other messages."""
        self.logger.info("Waiting for heavyweight signal")
        while True:
            try:
                msg = await self.receive_message()
                if msg is None:
                    await asyncio.sleep(NetworkConfig.RETRY_DELAY)
                    continue

                if msg.msg_type == MessageType.ACTION:
                    self.logger.info("Received ACTION signal from heavyweight")
                    break
                elif msg.msg_type == MessageType.REQUEST:
                    await self.handle_request(msg)
                elif msg.msg_type == MessageType.RELEASE:
                    await self.handle_release(msg)

            except Exception as e:
                self.logger.error(f"Error in wait_heavyweight: {e}")
                await asyncio.sleep(NetworkConfig.RETRY_DELAY)

    async def _run_loop(self) -> None:
        """Execute main process loop.

        Implements basic lightweight process behavior:
        1. Wait for heavyweight signal
        2. Request critical section
        3. Execute critical section
        4. Release critical section
        5. Notify heavyweight
        """
        while True:
            try:
                self.logger.info("Starting new cycle")
                await self.wait_heavyweight()
                self.logger.info("Requesting critical section")
                await self.request_cs()
                self.logger.info("Executing critical section")
                await self.execute_cs()
                self.logger.info("Releasing critical section")
                await self.release_cs()
                self.logger.info("Notifying heavyweight")
                await self.notify_heavyweight()
            except Exception as e:
                self.logger.error(f"Error in run loop: {e}")
                if not isinstance(e, asyncio.TimeoutError):
                    await asyncio.sleep(NetworkConfig.RETRY_DELAY)

    async def request_cs(self) -> None:
        """Request access to critical section."""
        raise NotImplementedError("Subclasses must implement request_cs()")

    async def execute_cs(self) -> None:
        """Execute critical section."""
        raise NotImplementedError("Subclasses must implement execute_cs()")

    async def release_cs(self) -> None:
        """Release critical section."""
        raise NotImplementedError("Subclasses must implement release_cs()")

    async def notify_heavyweight(self) -> None:
        """Notify heavyweight process of completion."""
        raise NotImplementedError("Subclasses must implement notify_heavyweight()")

    async def handle_request(self, msg: Message) -> None:
        """Handle request message from another process."""
        raise NotImplementedError("Subclasses must implement handle_request()")

    async def handle_release(self, msg: Message) -> None:
        """Handle release message from another process."""
        raise NotImplementedError("Subclasses must implement handle_release()")