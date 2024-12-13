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
from src.algorithms.vector_clock import VectorClock
from .heavyweight_process import HeavyweightProcess

@dataclass
class HeavyweightProcessB(HeavyweightProcess):
    """Implementation of heavyweight process B using Ricart-Agrawala's algorithm.

    This class coordinates lightweight processes using Ricart-Agrawala's algorithm,
    managing process initialization, message routing, and critical section access.

    Attributes:
        number: Process number within group B.
        port: Port number for network communication.
        clock: Vector clock for event ordering.
        lightweight_ports: Mapping of lightweight process IDs to ports.
        active_processes: Set of currently active lightweight processes.
        request_queue: Queue of processes requesting critical section.
        current_process: Currently executing lightweight process.
    """
    number: int = field(default=0)
    port: int = field(default=0)
    clock: VectorClock = field(default_factory=lambda: VectorClock("HWB", ["HWA", "HWB"]))
    lightweight_ports: Dict[str, int] = field(default_factory=dict)
    active_processes: Set[str] = field(default_factory=set)
    request_queue: List[str] = field(default_factory=list)
    current_process: str = field(default="")

    def __init__(self, number: int = 0, port: int = 0):
        """Initialize the process.

        Args:
            number: Process number within group B.
            port: Port number for network communication.
        """
        # Initialize dataclass fields first
        self.number = number
        self.port = port
        self.clock = VectorClock("HWB", ["HWA", "HWB"])
        self.lightweight_ports = {}
        self.active_processes = set()
        self.request_queue = []
        self.current_process = ""

        # Create process ID and initialize parent
        process_id = ProcessId(
            process_type="HEAVY",
            group="B",
            number=number
        )
        super().__init__(process_id=str(process_id), port=port)

        # Initialize lightweight process ports
        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            process_id = f"LWB{i}"
            port = NetworkConfig.LIGHTWEIGHT_BASE_PORT + NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES + i
            self.lightweight_ports[process_id] = port
            self.active_processes.add(process_id)

    def _init_vector_from_scalar(self, scalar_timestamp: int) -> Dict[str, int]:
        """Convert a scalar timestamp to a vector timestamp.

        Args:
            scalar_timestamp: Scalar timestamp to convert.

        Returns:
            Dictionary mapping process IDs to timestamp values.
        """
        vector = {}
        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            vector[str(i)] = scalar_timestamp if i == self.number else 0
        return vector

    async def _run_loop(self) -> None:
        """Main process loop implementing Ricart-Agrawala's algorithm.

        Repeatedly:
        1. Selects next process from request queue
        2. Grants critical section access
        3. Waits for process completion
        4. Releases critical section
        """
        while True:
            try:
                if not self.current_process and self.request_queue:
                    # Select next process
                    self.current_process = self.request_queue.pop(0)
                    self.logger.info(f"Selected process {self.current_process}")

                    # Grant critical section access
                    await self.grant_cs(self.current_process)

                # Handle incoming messages
                msg = await self.receive_message()
                self.logger.debug(f"Received message: {msg}")

                if msg.msg_type == MessageType.REQUEST:
                    await self.handle_request(msg)
                elif msg.msg_type == MessageType.REPLY:
                    await self.handle_reply(msg)

            except Exception as e:
                self.logger.error(f"Error in run loop: {e}")
                if not isinstance(e, asyncio.TimeoutError):
                    await asyncio.sleep(NetworkConfig.RETRY_DELAY)

    async def handle_request(self, msg: Message) -> None:
        """Handle request message from a lightweight process.

        Args:
            msg: Request message from lightweight process.

        Updates vector clock and adds process to request queue if not
        already present.
        """
        if isinstance(msg.timestamp, int):
            vector_ts = self._init_vector_from_scalar(msg.timestamp)
        else:
            vector_ts = msg.timestamp
        self.clock.update(vector_ts)
        sender_id = msg.sender_id

        if sender_id not in self.request_queue and sender_id != self.current_process:
            self.request_queue.append(sender_id)
            self.logger.info(f"Added {sender_id} to request queue")

    async def handle_reply(self, msg: Message) -> None:
        """Handle reply message from a lightweight process.

        Args:
            msg: Reply message from lightweight process.

        Updates vector clock and releases critical section for completed process.
        """
        if isinstance(msg.timestamp, int):
            vector_ts = self._init_vector_from_scalar(msg.timestamp)
        else:
            vector_ts = msg.timestamp
        self.clock.update(vector_ts)
        sender_id = msg.sender_id

        if sender_id == self.current_process:
            self.logger.info(f"Process {sender_id} completed critical section")
            self.current_process = ""

    async def grant_cs(self, process_id: str) -> None:
        """Grant critical section access to a lightweight process.

        Args:
            process_id: ID of process to grant access to.

        Sends ACTION message to process with current vector timestamp.
        """
        self.clock.increment()
        action_msg = Message(
            msg_type=MessageType.ACTION,
            sender_id=f"HW{self.process_id.group}",
            timestamp=self.clock.get_timestamp(),
            receiver_id=process_id
        )

        port = self.lightweight_ports[process_id]
        await self.send_message(action_msg, port)
        self.logger.info(f"Granted CS access to {process_id}")

async def main():
    """Main entry point for heavyweight process B.

    Parses command line arguments, creates and runs the process.

    Command line arguments:
        process_number: Process number within group B.
        port: Port number for network communication.
    """
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
        process.cleanup()
    except Exception as e:
        process.logger.error(f"Process terminated with error: {e}")
        process.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

# Agent 1 is done