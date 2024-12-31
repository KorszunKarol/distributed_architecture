from abc import ABC, abstractmethod
from typing import Optional, Any
from src.proto import replication_pb2

class BaseReplication(ABC):
    """Abstract base class for replication strategies.

    This class defines the interface that all replication strategies must implement.
    Each strategy handles when and how updates are propagated between nodes.

    Attributes:
        node: Reference to the node using this strategy
        propagation_type: Whether replication is active or passive
        consistency_type: Whether replication is eager or lazy
    """

    def __init__(self, propagation_type: str, consistency_type: str):
        """Initialize replication strategy.

        Args:
            propagation_type: Either 'active' or 'passive'
            consistency_type: Either 'eager' or 'lazy'
        """
        self.node = None
        self.propagation_type = propagation_type
        self.consistency_type = consistency_type
        self._running = False

    def set_node(self, node: Any) -> None:
        """Set the node reference.

        Args:
            node: Node instance using this strategy
        """
        self.node = node

    @abstractmethod
    async def handle_update(self, data_item: replication_pb2.DataItem) -> bool:
        """Handle an update to be replicated.

        Args:
            data_item: The data item to be replicated

        Returns:
            bool: True if update was handled successfully

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    async def sync(self) -> None:
        """Synchronize state with other nodes.

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    async def start(self) -> None:
        """Start the replication strategy."""
        self._running = True

    async def stop(self) -> None:
        """Stop the replication strategy."""
        self._running = False