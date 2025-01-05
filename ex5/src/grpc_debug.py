"""gRPC debugging utilities."""
import asyncio
import grpc
import logging
from typing import Any, Callable
from google.protobuf.json_format import MessageToDict
from grpc import ChannelConnectivity
import json

class DebugInterceptor(grpc.aio.ServerInterceptor):
    """Intercept and log all gRPC calls."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.logger = logging.getLogger(f"grpc.debug.{node_id}")

    async def intercept_service(
        self,
        continuation: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.HandlerCallDetails:
        method = handler_call_details.method
        if isinstance(method, bytes):
            method = method.decode()

        self.logger.debug(f"Received gRPC call: {method}")
        return await continuation(handler_call_details)

class DebugClientInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    """Intercept and log all outgoing gRPC calls."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.logger = logging.getLogger(f"grpc.debug.client.{node_id}")

    async def intercept_unary_unary(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any
    ) -> Any:
        method = client_call_details.method
        if isinstance(method, bytes):
            method = method.decode()

        try:
            # Log request
            req_dict = MessageToDict(request)
            self.logger.debug(
                f"Outgoing Request:\n"
                f"Method: {method}\n"
                f"Payload: {json.dumps(req_dict, indent=2)}"
            )

            # Make the call
            response = await continuation(client_call_details, request)

            # Log response
            resp_dict = MessageToDict(response)
            self.logger.debug(
                f"Received Response:\n"
                f"Method: {method}\n"
                f"Payload: {json.dumps(resp_dict, indent=2)}"
            )

            return response

        except Exception as e:
            self.logger.error(f"gRPC call failed: {str(e)}", exc_info=True)
            raise

async def _log_connectivity_changes(channel: grpc.aio.Channel, node_id: str, target: str):
    """Log channel connectivity changes."""
    logger = logging.getLogger(f"grpc.channel.{node_id}")
    async for state in channel.subscribe_connectivity_change():
        logger.info(f"Connection to {target} changed to: {ChannelConnectivity.Name(state)}")

async def create_channel(address: str, node_id: str) -> grpc.aio.Channel:
    """Create a gRPC channel with debugging enabled."""
    logger = logging.getLogger(f"grpc.channel.{node_id}")
    logger.info(f"Creating channel to {address}")

    # Create channel with debugging options
    channel = grpc.aio.insecure_channel(
        address,
        options=[
            ('grpc.enable_http_proxy', 0),
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.min_ping_interval_without_data_ms', 5000),
        ]
    )

    # Instead of using intercept_channel, create an interceptor chain
    interceptor = DebugClientInterceptor(node_id)

    # Wrap the channel with the interceptor
    wrapped_channel = grpc.aio.Channel(
        channel._channel,
        interceptors=[interceptor]
    )

    # Start monitoring connectivity
    asyncio.create_task(_log_connectivity_changes(channel, node_id, address))

    return wrapped_channel