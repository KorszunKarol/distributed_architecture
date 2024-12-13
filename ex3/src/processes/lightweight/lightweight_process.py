"""Base lightweight process implementation."""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.common.message import Message, MessageType
from src.common.constants import NetworkConfig
from src.processes.base_process import BaseProcess

@dataclass
class LightweightProcess(BaseProcess):
    """Base class for lightweight processes."""