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
                NetworkConfig.HOST,
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
            data = await reader.read(NetworkConfig.BUFFER_SIZE)
            if data:
                json_data = json.loads(data.decode())
                msg = Message.from_json(json_data)
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

    async def send_message(self, msg: Message, port: int) -> None:
        """Send message to specified port.

        Args:
            msg: Message to send
            port: Destination port
        """
        try:
            reader, writer = await asyncio.open_connection(
                NetworkConfig.HOST,
                port
            )

            # Convert message to JSON-serializable format
            json_data = json.dumps(msg.to_json())
            writer.write(json_data.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        except Exception as e:
            self.logger.error(f"Error sending message to port {port}: {e}")

    async def receive_message(self) -> Optional[Message]:
        """Receive and parse incoming message.

        Returns:
            Parsed message or None if error/timeout
        """
        try:
            msg = await asyncio.wait_for(
                self._message_queue.get(),
                timeout=NetworkConfig.MESSAGE_TIMEOUT
            )
            return msg
        except asyncio.TimeoutError:
            pass
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

    def _update_process_id(self, process_id: str) -> None:
        """Update process ID and reinitialize logger.

        Args:
            process_id: New process ID
        """
        self.process_id = process_id
        # Reinitialize logger with new process ID
        self.logger = logging.getLogger(self.process_id)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
