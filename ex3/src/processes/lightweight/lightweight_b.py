"""Lightweight process B implementation using Ricart-Agrawala's algorithm."""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.common.message import Message, MessageType, ProcessId
from src.common.constants import NetworkConfig
from src.algorithms.vector_clock import VectorClock
from .lightweight_process import LightweightProcess

@dataclass
class LightweightProcessB(LightweightProcess):
    """Implementation of lightweight process using Ricart-Agrawala's algorithm."""
    number: int = field(default=0)
    port: int = field(default=0)
    clock: VectorClock = field(default_factory=lambda: VectorClock("LWB", ["LWA", "LWB"]))
    request_queue: Set[str] = field(default_factory=set)
    reply_count: int = field(default=0)
    requesting_cs: bool = field(default=False)
    request_timestamp: Dict[str, int] = field(default_factory=dict)
    _line_number: int = field(default=1)

    def __init__(self, number: int = 0, port: int = 0):
        """Initialize the process.

        Args:
            number: Process number within group B.
            port: Port number for network communication.
        """
        # Initialize dataclass fields first
        self.number = number
        self.port = port
        self.clock = VectorClock("LWB", ["LWA", "LWB"])
        self.request_queue = set()
        self.reply_count = 0
        self.requesting_cs = False
        self.request_timestamp = {}
        self._line_number = 1

        # Create process ID and initialize parent
        process_id = ProcessId(
            process_type="LIGHT",
            group="B",
            number=number
        )
        super().__init__(process_id=str(process_id), port=port)