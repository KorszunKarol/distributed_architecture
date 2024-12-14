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
    clock: LamportClock = field(default_factory=LamportClock)
    request_queue: PriorityQueue = field(default_factory=PriorityQueue)
    acknowledgements: Set[str] = field(default_factory=set)
    requesting_cs: bool = field(default=False)
    request_timestamp: int = field(default=0)

    def __init__(self, number: int = 0, port: int = 0):
        """Initialize lightweight process A."""
        super().__init__(group="A", number=number, port=port)

        # Initialize algorithm-specific attributes
        self.clock = LamportClock()
        self.request_queue = PriorityQueue()
        self.acknowledgements = set()
        self.requesting_cs = False
        self.request_timestamp = 0

    async def execute_cs(self) -> None:
        """Execute critical section."""
        # Log Lamport condition check
        self.logger.info("LAMPORT CHECK: Process is at top of queue and has all acknowledgements")
        if not self.request_queue.empty():
            timestamp, proc_id = self.request_queue.queue[0]
            self.logger.info(f"LAMPORT CHECK: Queue top - Process {proc_id} with timestamp {timestamp}")
            self.logger.info(f"LAMPORT CHECK: Current process {self.get_process_id()} with timestamp {self.request_timestamp}")
            self.logger.info(f"LAMPORT CHECK: Acknowledgements received from {self.acknowledgements}")

        for i in range(ProcessConfig.DISPLAY_COUNT):
            print(f"{self._line_number} I'm lightweight process A{self.number + 1}")
            self._line_number += 1
            await asyncio.sleep(ProcessConfig.DISPLAY_TIME)

    async def request_cs(self) -> None:
        """Request access to critical section using Lamport's algorithm."""
        self.requesting_cs = True
        self.clock.increment()
        self.request_timestamp = self.clock.get_timestamp()
        self.acknowledgements.clear()

        # Log Lamport step 1: Push own request
        self.logger.info("LAMPORT STEP 1: Pushing own request to priority queue")
        self.request_queue.put((self.request_timestamp, self.get_process_id()))
        self.logger.info(f"LAMPORT STEP 1: Added own request with timestamp {self.request_timestamp}")

        # Log Lamport step 2: Broadcast request
        self.logger.info("LAMPORT STEP 2: Broadcasting request to all other processes")
        request_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id=self.get_process_id(),
            timestamp=self.request_timestamp
        )

        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            if i != self.number:
                port = NetworkConfig.LIGHTWEIGHT_A_BASE_PORT + i
                try:
                    await self.send_message(request_msg, port)
                    self.logger.info(f"LAMPORT STEP 2: Sent request to process at port {port}")
                except Exception as e:
                    self.logger.error(f"Failed to send request to process {i}: {e}")

        # Log Lamport step 3: Wait for acknowledgements
        self.logger.info("LAMPORT STEP 3: Waiting for acknowledgements from all processes")
        while len(self.acknowledgements) < NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES - 1:
            msg = await self.receive_message()
            if msg is None:
                await asyncio.sleep(NetworkConfig.RETRY_DELAY)
                continue

            if msg.msg_type == MessageType.ACKNOWLEDGEMENT:
                self.clock.update(msg.timestamp)
                self.acknowledgements.add(msg.sender_id)
                self.logger.info(f"LAMPORT STEP 3: Received acknowledgement from {msg.sender_id}")
            elif msg.msg_type == MessageType.REQUEST:
                await self.handle_request(msg)
            elif msg.msg_type == MessageType.RELEASE:
                await self.handle_release(msg)

        self.logger.info("LAMPORT STEP 3: Received all acknowledgements")

    async def release_cs(self) -> None:
        """Release critical section."""
        self.requesting_cs = False
        self.clock.increment()

        # Log Lamport step 4: Remove own request and broadcast release
        self.logger.info("LAMPORT STEP 4: Removing own request from queue and broadcasting release")
        temp_queue = PriorityQueue()
        while not self.request_queue.empty():
            timestamp, proc_id = self.request_queue.get()
            if proc_id != self.get_process_id():
                temp_queue.put((timestamp, proc_id))
        self.request_queue = temp_queue
        self.logger.info("LAMPORT STEP 4: Removed own request from queue")

        release_msg = Message(
            msg_type=MessageType.RELEASE,
            sender_id=self.get_process_id(),
            timestamp=self.clock.get_timestamp()
        )

        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            if i != self.number:
                port = NetworkConfig.LIGHTWEIGHT_A_BASE_PORT + i
                try:
                    await self.send_message(release_msg, port)
                    self.logger.info(f"LAMPORT STEP 4: Sent release to process at port {port}")
                except Exception as e:
                    self.logger.error(f"Failed to send release to process {i}: {e}")

    async def notify_heavyweight(self) -> None:
        """Notify heavyweight process of completion."""
        notify_msg = Message(
            msg_type=MessageType.ACKNOWLEDGEMENT,
            sender_id=self.get_process_id(),
            timestamp=self.clock.get_timestamp(),
            receiver_id=f"HW{self._process_id_obj.group}"
        )
        await self.send_message(notify_msg, NetworkConfig.HEAVYWEIGHT_A_PORT)
        self.logger.info("LAMPORT FINAL: Notified heavyweight process of completion")

    async def handle_request(self, msg: Message) -> None:
        """Handle request message from another process."""
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        # Log Lamport other process step 1
        self.logger.info("LAMPORT OTHER 1: Received request, adding to queue and sending acknowledgement")
        self.request_queue.put((msg.timestamp, sender_id))
        self.logger.info(f"LAMPORT OTHER 1: Added request from {sender_id} with timestamp {msg.timestamp}")

        ack_msg = Message(
            msg_type=MessageType.ACKNOWLEDGEMENT,
            sender_id=self.get_process_id(),
            timestamp=self.clock.get_timestamp(),
            receiver_id=sender_id
        )

        process_num = int(sender_id[-1]) - 1
        port = NetworkConfig.LIGHTWEIGHT_A_BASE_PORT + process_num
        await self.send_message(ack_msg, port)
        self.logger.info(f"LAMPORT OTHER 1: Sent acknowledgement to {sender_id}")

    async def handle_release(self, msg: Message) -> None:
        """Handle release message from another process."""
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        # Log Lamport other process step 2
        self.logger.info("LAMPORT OTHER 2: Received release, removing request from queue")
        temp_queue = PriorityQueue()
        while not self.request_queue.empty():
            timestamp, proc_id = self.request_queue.get()
            if proc_id != sender_id:
                temp_queue.put((timestamp, proc_id))
        self.request_queue = temp_queue
        self.logger.info(f"LAMPORT OTHER 2: Removed request from {sender_id} from queue")

async def main():
    """Main entry point for lightweight process A."""
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
        await process.cleanup()
    except Exception as e:
        process.logger.error(f"Process terminated with error: {e}")
        await process.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())