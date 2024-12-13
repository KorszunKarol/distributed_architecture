"""Base class for logical clocks in distributed systems.

This module provides the abstract base class for implementing logical clocks
used in distributed algorithms, such as Lamport's logical clock and vector clocks.
"""
from abc import ABC, abstractmethod

class BaseClock(ABC):
    """Abstract base class for logical clocks.

    This class defines the interface that all logical clock implementations
    must follow. Subclasses must implement the increment, update, and
    get_timestamp methods.
    """

    @abstractmethod
    def increment(self) -> None:
        """Increment the clock value.

        Must be implemented by subclasses to define how the clock advances.
        """
        pass

    @abstractmethod
    def update(self, timestamp) -> None:
        """Update the clock based on a received timestamp.

        Args:
            timestamp: The timestamp to update the clock with.
        """
        pass

    @abstractmethod
    def get_timestamp(self):
        """Get the current timestamp.

        Returns:
            The current timestamp in the format specific to the clock implementation.
        """
        pass