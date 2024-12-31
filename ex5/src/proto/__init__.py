"""Protocol buffer definitions for the replication system."""
from .replication_pb2 import *
from .replication_pb2_grpc import *

# This ensures the modules are available when importing from src.proto
__all__ = (
    'replication_pb2',
    'replication_pb2_grpc'
)