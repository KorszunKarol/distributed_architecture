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
        msg_type: Type of message (MessageType enum).
        sender_id: ID of the sending process.
        timestamp: Logical timestamp of the message.
        receiver_id: ID of the receiving process (optional).
        data: Additional message data (optional).
    """
    msg_type: MessageType
    sender_id: str
    timestamp: int
    receiver_id: Optional[str] = None
    data: Optional[Any] = None