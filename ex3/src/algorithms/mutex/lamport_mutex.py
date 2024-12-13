"""Lamport's mutual exclusion algorithm implementation.

This module implements Lamport's algorithm for distributed mutual exclusion,
using logical clocks to maintain causal ordering of requests and ensure
fair access to the critical section.
"""
from dataclasses import dataclass, field
from queue import PriorityQueue
from typing import Optional, Set
from ...common.message import Message, MessageType
from ...common.constants import NetworkConfig
from ..lamport_clock import LamportClock
from .base_mutex import BaseMutex

@dataclass
class LamportMutex(BaseMutex):
    """Implementation of Lamport's mutual exclusion algorithm.

    This class implements Lamport's algorithm for distributed mutual exclusion,
    using logical clocks and a priority queue to manage critical section access.

    Attributes:
        process_id: Identifier of the process using this mutex.
        clock: Lamport logical clock for event ordering.
        request_queue: Priority queue for ordering requests.
        acknowledgements: Set of processes that have acknowledged request.
        request_timestamp: Timestamp of current request.
    """
    clock: LamportClock = field(default_factory=LamportClock)
    request_queue: PriorityQueue = field(default_factory=lambda: PriorityQueue())
    acknowledgements: Set[str] = field(default_factory=set)
    request_timestamp: int = field(default=0)

    async def request_cs(self) -> None:
        """Request access to the critical section.

        Implements Lamport's algorithm:
        1. Increments logical clock
        2. Adds own request to queue
        3. Broadcasts request to all other processes
        4. Waits for acknowledgements from all processes
        """
        self.requesting_cs = True
        self.clock.increment()
        self.request_timestamp = self.clock.get_timestamp()
        self.acknowledgements.clear()

        self.request_queue.put((self.request_timestamp, self.process_id))

        request_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id=self.process_id,
            timestamp=self.request_timestamp
        )

        return request_msg

    async def release_cs(self) -> None:
        """Release the critical section.

        Implements Lamport's algorithm:
        1. Removes own request from queue
        2. Broadcasts release message to all processes
        """
        self.requesting_cs = False
        self.in_critical_section = False
        self.clock.increment()

        temp_queue = PriorityQueue()
        while not self.request_queue.empty():
            timestamp, proc_id = self.request_queue.get()
            if proc_id != self.process_id:
                temp_queue.put((timestamp, proc_id))
        self.request_queue = temp_queue

        release_msg = Message(
            msg_type=MessageType.RELEASE,
            sender_id=self.process_id,
            timestamp=self.clock.get_timestamp()
        )

        return release_msg

    async def handle_request(self, msg: Message) -> Optional[Message]:
        """Handle a request message from another process.

        Args:
            msg: Request message from another process.

        Returns:
            Acknowledgement message if request should be granted.
        """
        self.clock.update(msg.timestamp)
        sender_id = msg.sender_id

        self.request_queue.put((msg.timestamp, sender_id))

        ack_msg = Message(
            msg_type=MessageType.ACKNOWLEDGEMENT,
            sender_id=self.process_id,
            timestamp=self.clock.get_timestamp(),
            receiver_id=sender_id
        )

        return ack_msg

    async def handle_reply(self, msg: Message) -> None:
        """Handle a reply message from another process.

        Args:
            msg: Reply message from another process.
        """
        self.clock.update(msg.timestamp)
        self.acknowledgements.add(msg.sender_id)

    def is_allowed_to_enter(self) -> bool:
        """Check if the process can enter the critical section.

        Returns:
            True if all acknowledgements received and request is at queue head.
        """
        if not self.requesting_cs:
            return False

        if len(self.acknowledgements) < NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES - 1:
            return False

        if self.request_queue.empty():
            return False

        timestamp, proc_id = self.request_queue.queue[0]
        return proc_id == self.process_id