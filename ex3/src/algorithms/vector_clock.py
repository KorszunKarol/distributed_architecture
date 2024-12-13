"""Vector Clock implementation for distributed systems.

This module provides a Vector Clock implementation for tracking causality
and maintaining partial ordering of events in distributed systems.
"""

from typing import Dict, List
from .base_clock import BaseClock

class VectorClock(BaseClock):
    """A Vector clock implementation.

    Implements vector clock algorithm for tracking causality between events
    in distributed systems.

    Attributes:
        timestamps: Dictionary mapping process IDs to their logical timestamps.
        process_id: ID of the process owning this clock.
    """

    def __init__(self, process_id: str, process_ids: List[str]):
        """Initialize vector clock for a process.

        Args:
            process_id: ID of the process owning this clock.
            process_ids: List of all process IDs in the system.
        """
        self.process_id = process_id
        self.timestamps: Dict[str, int] = {pid: 0 for pid in process_ids}

    def get_timestamp(self) -> Dict[str, int]:
        """Get current vector timestamp.

        Returns:
            Dictionary mapping process IDs to their timestamps.
        """
        return self.timestamps.copy()

    def update(self, received_timestamps: Dict[str, int]) -> None:
        """Update clock based on received vector timestamp.

        Takes element-wise maximum of local and received timestamps.

        Args:
            received_timestamps: Vector timestamp received from another process.
        """
        for pid in self.timestamps:
            self.timestamps[pid] = max(
                self.timestamps[pid],
                received_timestamps.get(pid, 0)
            )
        self.increment()

    def increment(self) -> None:
        """Increment local process timestamp.

        Increments only the timestamp of the local process.
        """
        self.timestamps[self.process_id] += 1

    def is_concurrent_with(self, other_timestamp: Dict[str, int]) -> bool:
        """Check if this timestamp is concurrent with another.

        Args:
            other_timestamp: Another vector timestamp to compare with.

        Returns:
            True if timestamps are concurrent (incomparable), False otherwise.
        """
        less_than = False
        greater_than = False

        for pid in self.timestamps:
            if self.timestamps[pid] < other_timestamp.get(pid, 0):
                less_than = True
            elif self.timestamps[pid] > other_timestamp.get(pid, 0):
                greater_than = True

            if less_than and greater_than:
                return True

        return False