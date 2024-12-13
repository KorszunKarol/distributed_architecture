"""Lightweight process A implementation using Lamport's algorithm."""
import asyncio
import sys
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Dict, Set
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig, ProcessConfig
from src.algorithms.lamport_clock import LamportClock
from .lightweight_process import LightweightProcess

@dataclass
class LightweightProcessA(LightweightProcess):
    """
    Implementation of lightweight process using Lamport's algorithm.
    Messages follow REQUEST -> ACKNOWLEDGEMENT -> RELEASE sequence.
    """
    number: int = field(default=0)
    port: int = field(default=0)
    clock: LamportClock = field(default_factory=LamportClock)
    request_queue: PriorityQueue = field(default_factory=lambda: PriorityQueue())
    acknowledgements: Set[str] = field(default_factory=set)
    requesting_cs: bool = field(default=False)
    request_timestamp: int = field(default=0)
    _line_number: int = field(default=1)

    def __init__(self, number: int = 0, port: int = 0):
        """Initialize the process.

        Args:
            number: Process number within group A.
            port: Port number for network communication.
        """
        # Initialize dataclass fields first
        self.number = number
        self.port = port
        self.clock = LamportClock()
        self.request_queue = PriorityQueue()
        self.acknowledgements = set()
        self.requesting_cs = False
        self.request_timestamp = 0
        self._line_number = 1

        # Create process ID and initialize parent
        process_id = ProcessId(
            process_type="LIGHT",
            group="A",
            number=number
        )
        super().__init__(process_id=str(process_id), port=port)

    def get_process_id(self) -> str:
        """Get formatted process ID."""
        return f"LW{self.process_id.group}{self.number}"

    async def _run_loop(self) -> None:
        """Main process loop that implements Lamport's algorithm."""
        while True:
            try:
                # Wait for signal from heavyweight process
                await self.wait_heavyweight()

                # Request critical section
                await self.request_cs()

                # Execute critical section
                for i in range(10):
                    print(f"{self._line_number} I'm lightweight process A{self.number + 1}")
                    self._line_number += 1
                    await asyncio.sleep(1)

                # Release critical section
                await self.release_cs()

                # Notify heavyweight process
                await self.notify_heavyweight()

            except Exception as e:
                self.logger.error(f"Error in run loop: {e}")
                if not isinstance(e, asyncio.TimeoutError):
                    await asyncio.sleep(NetworkConfig.RETRY_DELAY)

    async def request_cs(self) -> None:
        """Request access to critical section using Lamport's algorithm."""
        self.requesting_cs = True
        self.clock.increment()
        self.request_timestamp = self.clock.get_timestamp()
        self.acknowledgements.clear()

        # Add own request to queue
        self.request_queue.put((self.request_timestamp, self.get_process_id()))

        # Broadcast request to all other processes
        request_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id=self.get_process_id(),
            timestamp=self.request_timestamp
        )

        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            if i != self.number:
                port = NetworkConfig.LIGHTWEIGHT_BASE_PORT + i
                try:
                    await self.send_message(request_msg, port)
                except Exception as e:
                    self.logger.error(f"Failed to send request to process {i}: {e}")

        # Wait for acknowledgements from all other processes
        while len(self.acknowledgements) < NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES - 1:
            msg = await self.receive_message()
            if msg.msg_type == MessageType.ACKNOWLEDGEMENT:
                self.clock.update(msg.timestamp)
                self.acknowledgements.add(msg.sender_id)
            elif msg.msg_type == MessageType.REQUEST:
                await self.handle_request(msg)
            elif msg.msg_type == MessageType.RELEASE:
                await self.handle_release(msg)

    async def handle_request(self, msg: Message) -> None:
        """Handle request message from another process."""
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        # Add request to queue
        self.request_queue.put((msg.timestamp, sender_id))

        # Always send acknowledgement immediately
        ack_msg = Message(
            msg_type=MessageType.ACKNOWLEDGEMENT,
            sender_id=self.get_process_id(),
            timestamp=self.clock.get_timestamp(),
            receiver_id=sender_id
        )

        process_num = int(sender_id[-1])
        port = NetworkConfig.LIGHTWEIGHT_BASE_PORT + process_num
        await self.send_message(ack_msg, port)

    async def handle_release(self, msg: Message) -> None:
        """Handle release message from another process."""
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        # Remove sender's request from queue
        temp_queue = PriorityQueue()
        while not self.request_queue.empty():
            timestamp, proc_id = self.request_queue.get()
            if proc_id != sender_id:
                temp_queue.put((timestamp, proc_id))
        self.request_queue = temp_queue

    async def release_cs(self) -> None:
        """Release critical section."""
        self.requesting_cs = False
        self.clock.increment()

        # Remove own request from queue
        temp_queue = PriorityQueue()
        while not self.request_queue.empty():
            timestamp, proc_id = self.request_queue.get()
            if proc_id != self.get_process_id():
                temp_queue.put((timestamp, proc_id))
        self.request_queue = temp_queue

        # Broadcast release to all other processes
        release_msg = Message(
            msg_type=MessageType.RELEASE,
            sender_id=self.get_process_id(),
            timestamp=self.clock.get_timestamp()
        )

        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            if i != self.number:
                port = NetworkConfig.LIGHTWEIGHT_BASE_PORT + i
                try:
                    await self.send_message(release_msg, port)
                except Exception as e:
                    self.logger.error(f"Failed to send release to process {i}: {e}")

    async def wait_heavyweight(self) -> None:
        """Wait for signal from heavyweight process.

        Waits for ACTION message from heavyweight process while handling
        any incoming REQUEST or RELEASE messages.
        """
        while True:
            msg = await self.receive_message()
            if msg.msg_type == MessageType.ACTION:
                self.clock.update(msg.timestamp)
                break
            elif msg.msg_type == MessageType.REQUEST:
                await self.handle_request(msg)
            elif msg.msg_type == MessageType.RELEASE:
                await self.handle_release(msg)

    async def notify_heavyweight(self) -> None:
        """Notify heavyweight process of completion.

        Sends ACKNOWLEDGEMENT message to heavyweight process indicating
        completion of critical section.
        """
        notify_msg = Message(
            msg_type=MessageType.ACKNOWLEDGEMENT,
            sender_id=self.get_process_id(),
            timestamp=self.clock.get_timestamp(),
            receiver_id=f"HW{self.process_id.group}"
        )
        await self.send_message(notify_msg, NetworkConfig.HEAVYWEIGHT_A_PORT)

async def main():
    """Main entry point for lightweight process A.

    Parses command line arguments, creates and runs the process.

    Command line arguments:
        process_number: Process number within group A.
        port: Port number for network communication.
    """
    if len(sys.argv) != 3:
        print("Usage: python lightweight_a.py <process_number> <port>")
        sys.exit(1)

    process_number = int(sys.argv[1])
    port = int(sys.argv[2])

    process = LightweightProcessA(
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