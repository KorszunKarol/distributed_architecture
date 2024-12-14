"""Base heavyweight process implementation."""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.algorithms.lamport_clock import LamportClock
from src.algorithms.vector_clock import VectorClock
from src.common.message import Message, MessageType
from src.common.constants import NetworkConfig
from src.processes.base_process import BaseProcess

@dataclass
class HeavyweightProcess(BaseProcess):
    """Base class for heavyweight processes.

    This class provides common functionality for heavyweight processes,
    including token management and coordination of lightweight processes.

    Attributes:
        has_token: Whether this process currently holds the token.
        token_held_time: How long the token has been held.
    """
    has_token: bool = field(default=False)
    token_held_time: float = field(default=0.0)
    active_processes: Set[str] = field(init=False)
    current_process: str = field(default="")

    def __init__(self, process_id: str, port: int):
        """Initialize heavyweight process.

        Args:
            process_id: Process identifier
            port: Network port for communication
        """
        super().__init__(process_id=process_id, port=port)
        self.active_processes = set()  # Initialize empty set here
        self.current_process = ""

    async def _run_loop(self) -> None:
        """Main process loop for heavyweight processes."""
        while True:
            try:
                if self.has_token:
                    self.logger.info(f"Starting new round with token. Active processes: {self.active_processes}")

                    # Signal each lightweight process in turn
                    for process_id in list(self.active_processes):  # Convert to list to avoid modification during iteration
                        self.current_process = process_id
                        self.logger.info(f"Granting access to {process_id}")
                        await self.grant_cs(process_id)

                        # Wait for this process to complete
                        while self.current_process == process_id:
                            msg = await self.receive_message()
                            if msg is None:
                                await asyncio.sleep(NetworkConfig.RETRY_DELAY)
                                continue

                            if msg.msg_type == MessageType.ACKNOWLEDGEMENT:
                                if msg.sender_id == process_id:
                                    self.logger.info(f"Process {process_id} completed")
                                    self.current_process = ""
                                    break
                            else:
                                await self.handle_message(msg)

                        await asyncio.sleep(0.1)  # Prevent flooding

                    # Pass token to other heavyweight process
                    self.logger.info("All lightweight processes completed, passing token")
                    await self.pass_token()
                    self.has_token = False
                else:
                    # Wait for token or messages
                    msg = await self.receive_message()
                    if msg is None:
                        await asyncio.sleep(NetworkConfig.RETRY_DELAY)
                        continue

                    if msg.msg_type == MessageType.TOKEN:
                        self.logger.info("Received token")
                        self.has_token = True
                    else:
                        await self.handle_message(msg)

                await asyncio.sleep(0.1)  # Prevent busy waiting

            except Exception as e:
                self.logger.error(f"Error in run loop: {e}")
                if not isinstance(e, asyncio.TimeoutError):
                    await asyncio.sleep(NetworkConfig.RETRY_DELAY)

    async def handle_message(self, msg: Message) -> None:
        """Handle incoming messages.

        Must be implemented by subclasses to handle their specific message types.

        Args:
            msg: The received message to handle.
        """
        raise NotImplementedError("Subclasses must implement handle_message()")

    async def pass_token(self) -> None:
        """Pass token to the other heavyweight process.

        Must be implemented by subclasses to handle token passing logic.
        """
        raise NotImplementedError("Subclasses must implement pass_token()")

    async def grant_cs(self, process_id: str) -> None:
        """Grant critical section access to a lightweight process.

        Must be implemented by subclasses to handle their specific granting logic.

        Args:
            process_id: ID of the process to grant access to.
        """
        raise NotImplementedError("Subclasses must implement grant_cs()")