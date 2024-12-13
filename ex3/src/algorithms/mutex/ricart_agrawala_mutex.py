"""Ricart-Agrawala's mutual exclusion algorithm implementation.

This module implements Ricart-Agrawala's algorithm for distributed mutual
exclusion, using vector clocks to maintain causal ordering of requests and
ensure fair access to the critical section.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from ...common.message import Message, MessageType
from ...common.constants import NetworkConfig
from ..vector_clock import VectorClock
from .base_mutex import BaseMutex

@dataclass
class RicartAgrawalaMutex(BaseMutex):
    """Implementation of Ricart-Agrawala's mutual exclusion algorithm.

    This class implements Ricart-Agrawala's algorithm for distributed mutual
    exclusion, using vector clocks and deferred replies to manage critical
    section access.

    Attributes:
        process_id: Identifier of the process using this mutex.
        clock: Vector clock for event ordering.
        request_queue: Set of deferred requests.
        reply_count: Number of replies received.
        request_timestamp: Vector timestamp of current request.
    """
    clock: VectorClock
    request_queue: Set[str] = field(default_factory=set)
    reply_count: int = field(default=0)
    request_timestamp: Dict[str, int] = field(default_factory=dict)

    async def request_cs(self) -> None:
        """Request access to the critical section.

        Implements Ricart-Agrawala's algorithm:
        1. Increments vector clock
        2. Broadcasts request to all other processes
        3. Waits for replies from all processes
        """
        self.requesting_cs = True
        self.clock.increment()
        self.reply_count = 0

        self.request_timestamp = self.clock.get_timestamp()

        request_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id=self.process_id,
            timestamp=self.request_timestamp,
            receiver_id="*"
        )

        return request_msg

    async def release_cs(self) -> None:
        """Release the critical section.

        Implements Ricart-Agrawala's algorithm:
        1. Increments vector clock
        2. Sends deferred replies to queued requests
        """
        self.requesting_cs = False
        self.in_critical_section = False
        self.clock.increment()

        release_timestamp = self.clock.get_timestamp()
        release_msg = Message(
            msg_type=MessageType.RELEASE,
            sender_id=self.process_id,
            timestamp=release_timestamp,
            receiver_id="*"
        )

        reply_messages = []
        for process_id in list(self.request_queue):
            reply_msg = Message(
                msg_type=MessageType.REPLY,
                sender_id=self.process_id,
                timestamp=self.clock.get_timestamp(),
                receiver_id=process_id
            )
            reply_messages.append(reply_msg)
            self.request_queue.remove(process_id)

        return release_msg, reply_messages

    async def handle_request(self, msg: Message) -> Optional[Message]:
        """Handle a request message from another process.

        Args:
            msg: Request message from another process.

        Returns:
            Reply message if request should be granted, None if deferred.
        """
        sender_id = msg.sender_id
        msg_timestamp = msg.timestamp

        if not self.requesting_cs:
            reply_msg = Message(
                msg_type=MessageType.REPLY,
                sender_id=self.process_id,
                timestamp=self.clock.get_timestamp(),
                receiver_id=sender_id
            )
            return reply_msg
        else:
            if self.clock.compare(msg_timestamp, sender_id):
                self.request_queue.add(sender_id)
                return None
            else:
                reply_msg = Message(
                    msg_type=MessageType.REPLY,
                    sender_id=self.process_id,
                    timestamp=self.clock.get_timestamp(),
                    receiver_id=sender_id
                )
                return reply_msg

    async def handle_reply(self, msg: Message) -> None:
        """Handle a reply message from another process.

        Args:
            msg: Reply message from another process.
        """
        self.clock.update(msg.timestamp)
        self.reply_count += 1

    def is_allowed_to_enter(self) -> bool:
        """Check if the process can enter the critical section.

        Returns:
            True if all replies received, False otherwise.
        """
        return (self.requesting_cs and
                self.reply_count >= NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES - 1)