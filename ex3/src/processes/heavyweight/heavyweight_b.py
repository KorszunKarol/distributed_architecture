"""Heavyweight process B implementation for distributed mutual exclusion.

This module implements a heavyweight process that coordinates lightweight processes
using Ricart-Agrawala's algorithm. It manages process initialization, message routing,
and critical section access coordination.
"""
import asyncio
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Set
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig, ProcessConfig
from src.algorithms.lamport_clock import LamportClock
from .heavyweight_process import HeavyweightProcess

@dataclass
class HeavyweightProcessB(HeavyweightProcess):
    """Implementation of heavyweight process B using Ricart-Agrawala's algorithm.

    This class coordinates lightweight processes using Ricart-Agrawala's algorithm,
    managing process initialization, message routing, and critical section access.

    Attributes:
        number: Process number within group B.
        port: Port number for network communication.
        clock: Lamport clock for event ordering.
        lightweight_ports: Mapping of lightweight process IDs to ports.
        request_queue: Queue of processes requesting critical section.
        current_process: Currently executing lightweight process.
        has_token: Indicates whether the process has the token.
        process_id: Process ID for logging purposes.
    """
    number: int = field(default=0)
    port: int = field(default=0)
    clock: LamportClock = field(default_factory=LamportClock)
    lightweight_ports: Dict[str, int] = field(default_factory=dict)
    request_queue: List[str] = field(default_factory=list)
    current_process: str = field(default="")
    has_token: bool = field(default=False)
    process_id: ProcessId = field(init=False)

    def __init__(self, number: int = 0, port: int = 0):
        """Initialize heavyweight process B.

        Args:
            number: Process number within group B.
            port: Port number for network communication.
        """
        # Create process ID
        self.process_id = ProcessId(
            process_type="HEAVY",
            group="B",
            number=number
        )

        # Initialize parent class with string representation for logging
        super().__init__(process_id=str(self.process_id), port=port)

        # Initialize own attributes
        self.number = number
        self.port = port
        self.clock = LamportClock()
        self.lightweight_ports = {}
        self.request_queue = []
        self.current_process = ""
        self.has_token = False

        # Initialize lightweight process ports and active processes
        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            process_id = f"LWB{i+1}"  # Use 1-based indexing for display
            port = NetworkConfig.LIGHTWEIGHT_B_BASE_PORT + i
            self.lightweight_ports[process_id] = port
            self.active_processes.add(process_id)
            self.logger.info(f"Added {process_id} to active processes")

    async def handle_message(self, msg: Message) -> None:
        """Handle incoming messages.

        Args:
            msg: The received message to handle.
        """
        if msg.msg_type == MessageType.REQUEST:
            await self.handle_request(msg)
        elif msg.msg_type == MessageType.ACKNOWLEDGEMENT:  # Changed from REPLY
            await self.handle_acknowledgement(msg)

    async def pass_token(self) -> None:
        """Pass token to heavyweight process A."""
        self.clock.increment()
        token_msg = Message(
            msg_type=MessageType.TOKEN,
            sender_id="HWB",
            timestamp=self.clock.get_timestamp(),
            receiver_id="HWA"
        )
        await self.send_message(token_msg, NetworkConfig.HEAVYWEIGHT_A_PORT)
        self.logger.info("Passed token to HWA")

    async def handle_request(self, msg: Message) -> None:
        """Handle request message from a lightweight process.

        Args:
            msg: Request message from lightweight process.

        Updates logical clock and adds process to request queue if not
        already present.
        """
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        if sender_id not in self.request_queue and sender_id != self.current_process:
            self.request_queue.append(sender_id)
            self.logger.info(f"Added {sender_id} to request queue")

    async def handle_acknowledgement(self, msg: Message) -> None:
        """Handle acknowledgement message from a lightweight process.

        Args:
            msg: Acknowledgement message from lightweight process.

        Updates logical clock and releases critical section for completed process.
        """
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        if sender_id == self.current_process:
            self.logger.info(f"Process {sender_id} completed critical section")
            self.current_process = ""

    async def grant_cs(self, process_id: str) -> None:
        """Grant critical section access to a lightweight process."""
        self.clock.increment()
        action_msg = Message(
            msg_type=MessageType.ACTION,
            sender_id="HWB",
            timestamp=self.clock.get_timestamp(),
            receiver_id=process_id
        )
        port = self.lightweight_ports[process_id]
        await self.send_message(action_msg, port)
        self.logger.info(f"Granting CS access to {process_id} on port {port}")

async def main():
    """Main entry point for heavyweight process B."""
    if len(sys.argv) != 3:
        print("Usage: python heavyweight_b.py <process_number> <port>")
        sys.exit(1)

    process_number = int(sys.argv[1])
    port = int(sys.argv[2])

    process = HeavyweightProcessB(
        number=process_number,
        port=port
    )

    try:
        await process.run()
    except KeyboardInterrupt:
        await process.cleanup()
    except Exception as e:
        process.logger.error(f"Process terminated with error: {e}")
        await process.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

# Agent 1 is done