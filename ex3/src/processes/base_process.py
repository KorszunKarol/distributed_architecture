"""Base process class for distributed mutual exclusion.

This module provides the base class for all processes in the distributed system,
implementing basic network communication and message handling.
"""
import asyncio
import logging
import json
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Awaitable
from src.common.message import Message, MessageType
from src.common.constants import NetworkConfig

@dataclass
class BaseProcess:
    """Base class for all processes in the distributed system.

    This class provides basic network communication and message handling
    functionality that all processes need.

    Attributes:
        process_id: Identifier for this process.
        port: Network port this process listens on.
        server: Asyncio server instance.
        message_handlers: Mapping of message types to handlers.
        logger: Logger for this process.
    """
    process_id: str
    port: int
    server: Optional[asyncio.AbstractServer] = field(init=False, default=None)
    message_handlers: Dict[MessageType, Callable[[Message], Awaitable[None]]] = field(default_factory=dict)
    logger: logging.Logger = field(init=False)
    _message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    def __post_init__(self):
        """Initialize the process.

        Sets up logging configuration.
        """
        self.logger = logging.getLogger(self.process_id)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def run(self) -> None:
        """Run the process.

        Starts network server and runs main process loop.
        """
        try:
            self.server = await asyncio.start_server(
                self._handle_connection,
                'localhost',
                self.port
            )
            async with self.server:
                await self._run_loop()
        finally:
            await self.cleanup()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming network connection.

        Args:
            reader: Stream reader for incoming data.
            writer: Stream writer for outgoing data.
        """
        try:
            data = await reader.read()
            if data:
                msg_dict = json.loads(data.decode())
                msg = Message(**msg_dict)
                await self._message_queue.put(msg)
        except Exception as e:
            self.logger.error(f"Error handling connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def _run_loop(self) -> None:
        """Main process loop.

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _run_loop()")

    async def send_message(self, msg: Message, target_port: int) -> None:
        """Send a message to another process.

        Args:
            msg: Message to send.
            target_port: Port to send message to.
        """
        try:
            reader, writer = await asyncio.open_connection('localhost', target_port)
            msg_data = json.dumps(msg.__dict__).encode()
            writer.write(msg_data)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            self.logger.error(f"Error sending message to port {target_port}: {e}")

    async def receive_message(self) -> Optional[Message]:
        """Receive and handle a message.

        Returns:
            Received message or None if error occurs.
        """
        try:
            msg = await self._message_queue.get()
            if msg and msg.msg_type in self.message_handlers:
                await self.message_handlers[msg.msg_type](msg)
            return msg
        except Exception as e:
            self.logger.error(f"Error receiving message: {e}")
            return None

    def register_handler(self, msg_type: MessageType,
                        handler: Callable[[Message], Awaitable[None]]) -> None:
        """Register a message handler.

        Args:
            msg_type: Type of message to handle.
            handler: Function to handle messages of this type.
        """
        self.message_handlers[msg_type] = handler

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
