"""Lightweight process B implementation using Ricart-Agrawala algorithm."""
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
class LightweightProcessB(LightweightProcess):
    """
    Implementation of lightweight process using Ricart-Agrawala algorithm.
    Messages follow REQUEST -> REPLY sequence.
    """
    clock: LamportClock = field(default_factory=LamportClock)
    deferred_replies: Set[str] = field(default_factory=set)
    replies_received: Set[str] = field(default_factory=set)
    requesting_cs: bool = field(default=False)
    request_timestamp: int = field(default=0)

    def __init__(self, number: int = 0, port: int = 0):
        """Initialize lightweight process B."""
        super().__init__(group="B", number=number, port=port)

        # Initialize algorithm-specific attributes
        self.clock = LamportClock()
        self.deferred_replies = set()
        self.replies_received = set()
        self.requesting_cs = False
        self.request_timestamp = 0

    async def execute_cs(self) -> None:
        """Execute critical section."""
        # Log Ricart-Agrawala condition check
        self.logger.info("RA CHECK: Process has received all replies")
        self.logger.info(f"RA CHECK: Replies received from {self.replies_received}")
        self.logger.info(f"RA CHECK: Current timestamp {self.request_timestamp}")

        for i in range(ProcessConfig.DISPLAY_COUNT):
            print(f"{self._line_number} I'm lightweight process B{self.number + 1}")
            self._line_number += 1
            await asyncio.sleep(ProcessConfig.DISPLAY_TIME)

    async def request_cs(self) -> None:
        """Request access to critical section using Ricart-Agrawala algorithm."""
        self.requesting_cs = True
        self.clock.increment()
        self.request_timestamp = self.clock.get_timestamp()
        self.replies_received.clear()
        self.logger.info(f"RA STEP 1: Requesting CS with timestamp {self.request_timestamp}")

        # Log Ricart-Agrawala step 1: Send request to all
        request_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id=self.get_process_id(),
            timestamp=self.request_timestamp
        )

        for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
            if i != self.number:
                port = NetworkConfig.LIGHTWEIGHT_B_BASE_PORT + i
                try:
                    await self.send_message(request_msg, port)
                    self.logger.info(f"RA STEP 1: Sent request to process at port {port}")
                except Exception as e:
                    self.logger.error(f"Failed to send request to process {i}: {e}")

        # Log Ricart-Agrawala step 2: Wait for all replies
        self.logger.info("RA STEP 2: Waiting for replies from all processes")
        while len(self.replies_received) < NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES - 1:
            msg = await self.receive_message()
            if msg is None:
                await asyncio.sleep(NetworkConfig.RETRY_DELAY)
                continue

            if msg.msg_type == MessageType.ACKNOWLEDGEMENT:  # Using ACKNOWLEDGEMENT as REPLY
                self.clock.update(msg.timestamp)
                self.replies_received.add(msg.sender_id)
                self.logger.info(f"RA STEP 2: Received reply from {msg.sender_id}")
            elif msg.msg_type == MessageType.REQUEST:
                await self.handle_request(msg)

        self.logger.info("RA STEP 2: Received all replies")

    async def release_cs(self) -> None:
        """Release critical section."""
        self.requesting_cs = False
        self.clock.increment()
        self.logger.info("RA STEP 3: Releasing CS")

        # Log Ricart-Agrawala step 3: Send replies to deferred requests
        self.logger.info(f"RA STEP 3: Sending replies to {len(self.deferred_replies)} deferred requests")
        for deferred_id in self.deferred_replies:
            reply_msg = Message(
                msg_type=MessageType.ACKNOWLEDGEMENT,  # Using ACKNOWLEDGEMENT as REPLY
                sender_id=self.get_process_id(),
                timestamp=self.clock.get_timestamp(),
                receiver_id=deferred_id
            )

            process_num = int(deferred_id[-1]) - 1
            port = NetworkConfig.LIGHTWEIGHT_B_BASE_PORT + process_num
            try:
                await self.send_message(reply_msg, port)
                self.logger.info(f"RA STEP 3: Sent deferred reply to {deferred_id}")
            except Exception as e:
                self.logger.error(f"Failed to send deferred reply to process {deferred_id}: {e}")

        self.logger.info(f"RA STEP 3: Sent {len(self.deferred_replies)} deferred replies")
        self.deferred_replies.clear()

    async def handle_request(self, msg: Message) -> None:
        """Handle request message from another process using Ricart-Agrawala rules."""
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        # Log Ricart-Agrawala request handling rules
        self.logger.info(f"RA HANDLE: Received request from {sender_id} with timestamp {msg.timestamp}")

        should_defer = (
            self.requesting_cs and (
                msg.timestamp > self.request_timestamp or
                (msg.timestamp == self.request_timestamp and sender_id > self.get_process_id())
            )
        )

        if should_defer:
            # Log Ricart-Agrawala defer case
            self.logger.info(f"RA HANDLE: Deferring reply to {sender_id} (requesting_cs={self.requesting_cs}, "
                           f"msg_ts={msg.timestamp}, own_ts={self.request_timestamp})")
            self.deferred_replies.add(sender_id)
            self.logger.info(f"RA HANDLE: Deferred reply to {sender_id}")
        else:
            # Log Ricart-Agrawala immediate reply case
            self.logger.info(f"RA HANDLE: Sending immediate reply to {sender_id} (requesting_cs={self.requesting_cs}, "
                           f"msg_ts={msg.timestamp}, own_ts={self.request_timestamp})")
            reply_msg = Message(
                msg_type=MessageType.ACKNOWLEDGEMENT,  # Using ACKNOWLEDGEMENT as REPLY
                sender_id=self.get_process_id(),
                timestamp=self.clock.get_timestamp(),
                receiver_id=sender_id
            )

            process_num = int(sender_id[-1]) - 1
            port = NetworkConfig.LIGHTWEIGHT_B_BASE_PORT + process_num
            await self.send_message(reply_msg, port)
            self.logger.info(f"RA HANDLE: Sent immediate reply to {sender_id}")

    async def notify_heavyweight(self) -> None:
        """Notify heavyweight process of completion."""
        notify_msg = Message(
            msg_type=MessageType.ACKNOWLEDGEMENT,
            sender_id=self.get_process_id(),
            timestamp=self.clock.get_timestamp(),
            receiver_id=f"HW{self._process_id_obj.group}"
        )
        await self.send_message(notify_msg, NetworkConfig.HEAVYWEIGHT_B_PORT)
        self.logger.info("Notified heavyweight process of completion")

async def main():
    """Main entry point for lightweight process B."""
    if len(sys.argv) != 3:
        print("Usage: python lightweight_b.py <process_number> <port>")
        sys.exit(1)

    process_number = int(sys.argv[1])
    port = int(sys.argv[2])

    process = LightweightProcessB(
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