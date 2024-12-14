"""Message types and process ID classes for the distributed mutual exclusion system.

This module defines the message types and process identifiers used in the distributed
mutual exclusion system. It includes enums for message types and dataclasses for
process IDs and messages.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional

class MessageType(Enum):
    """Types of messages that can be exchanged between processes.

    Attributes:
        REQUEST: Message requesting entry to critical section.
        ACKNOWLEDGEMENT: Message acknowledging a request.
        RELEASE: Message indicating release of critical section.
        TOKEN: Message for token passing between heavyweight processes.
        ACTION: Message from heavyweight to lightweight process.
    """
    REQUEST = auto()
    ACKNOWLEDGEMENT = auto()
    RELEASE = auto()
    TOKEN = auto()
    ACTION = auto()

@dataclass
class ProcessId:
    """Process identifier containing type, group, and number.

    Attributes:
        process_type: Type of process ("HEAVY" or "LIGHT").
        group: Process group identifier ("A" or "B").
        number: Process number within its group.
    """
    process_type: str
    group: str
    number: int

@dataclass
class Message:
    """Message exchanged between processes.

    Attributes:
        msg_type: Type of message (REQUEST, ACKNOWLEDGEMENT, etc.)
        sender_id: ID of sending process
        timestamp: Message timestamp
        receiver_id: ID of receiving process (optional)
        data: Additional message data (optional)
    """
    msg_type: MessageType
    sender_id: str
    timestamp: Any
    receiver_id: Optional[str] = None
    data: Optional[Any] = None

    def to_json(self) -> dict:
        """Convert message to JSON-serializable dict."""
        return {
            'msg_type': self.msg_type.name,  # Convert enum to string
            'sender_id': self.sender_id,
            'timestamp': self.timestamp,
            'receiver_id': self.receiver_id,
            'data': self.data
        }

    @classmethod
    def from_json(cls, data: dict) -> 'Message':
        """Create message from JSON dict."""
        data['msg_type'] = MessageType[data['msg_type']]  # Convert string back to enum
        return cls(**data)