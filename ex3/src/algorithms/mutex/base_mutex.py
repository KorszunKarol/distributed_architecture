"""Base class for distributed mutual exclusion algorithms.

This module provides the abstract base class for implementing distributed mutual
exclusion algorithms like Lamport's and Ricart-Agrawala's algorithms.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from ...common.message import Message

@dataclass
class BaseMutex(ABC):
    """Abstract base class for mutual exclusion algorithms.

    This class defines the interface that all mutual exclusion implementations
    must follow, providing methods for requesting, releasing, and managing
    critical section access.

    Attributes:
        process_id: Identifier of the process using this mutex.
        requesting_cs: Whether the process is currently requesting critical section.
        in_critical_section: Whether the process is in critical section.
    """
    process_id: str
    requesting_cs: bool = False
    in_critical_section: bool = False

    @abstractmethod
    async def request_cs(self) -> None:
        """Request access to the critical section.

        Implements the algorithm-specific logic for requesting critical section
        access. Must be implemented by concrete mutex classes.
        """
        pass

    @abstractmethod
    async def release_cs(self) -> None:
        """Release the critical section.

        Implements the algorithm-specific logic for releasing critical section
        access. Must be implemented by concrete mutex classes.
        """
        pass

    @abstractmethod
    async def handle_request(self, msg: Message) -> Optional[Message]:
        """Handle a request message from another process.

        Args:
            msg: The request message to handle.

        Returns:
            Optional response message to send back.
        """
        pass

    @abstractmethod
    async def handle_reply(self, msg: Message) -> None:
        """Handle a reply message from another process.

        Args:
            msg: The reply message to handle.
        """
        pass

    @abstractmethod
    def is_allowed_to_enter(self) -> bool:
        """Check if the process can enter the critical section.

        Returns:
            True if the process can enter the critical section, False otherwise.
        """
        pass