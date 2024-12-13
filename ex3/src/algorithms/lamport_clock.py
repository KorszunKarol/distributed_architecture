"""Lamport Clock implementation for distributed systems.

This module provides a Lamport Clock implementation for maintaining logical time
in distributed systems. It ensures a partial ordering of events across processes.
"""

from .base_clock import BaseClock

class LamportClock(BaseClock):
    """A Lamport logical clock implementation.

    Implements Lamport's logical clock algorithm for maintaining causal ordering
    of events in distributed systems.

    Attributes:
        timestamp: Current logical timestamp of this clock.
    """

    def __init__(self):
        """Initialize a new Lamport clock with timestamp 0."""
        self.timestamp = 0

    def get_timestamp(self) -> int:
        """Get current timestamp value.

        Returns:
            Current logical timestamp.
        """
        return self.timestamp

    def update(self, received_timestamp: int) -> None:
        """Update clock based on received timestamp.

        Updates local timestamp to be greater than both local time
        and received time.

        Args:
            received_timestamp: Timestamp received from another process.
        """
        self.timestamp = max(self.timestamp, received_timestamp) + 1

    def increment(self) -> None:
        """Increment local timestamp.

        Increments timestamp for local events.
        """
        self.timestamp += 1