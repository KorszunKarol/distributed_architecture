# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from src.proto import replication_pb2 as src_dot_proto_dot_replication__pb2

GRPC_GENERATED_VERSION = '1.68.1'
GRPC_VERSION = grpc.__version__
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    raise RuntimeError(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in src/proto/replication_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
    )


class NodeServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.ExecuteTransaction = channel.unary_unary(
                '/replication.NodeService/ExecuteTransaction',
                request_serializer=src_dot_proto_dot_replication__pb2.Transaction.SerializeToString,
                response_deserializer=src_dot_proto_dot_replication__pb2.TransactionResponse.FromString,
                _registered_method=True)
        self.PropagateUpdate = channel.unary_unary(
                '/replication.NodeService/PropagateUpdate',
                request_serializer=src_dot_proto_dot_replication__pb2.UpdateNotification.SerializeToString,
                response_deserializer=src_dot_proto_dot_replication__pb2.AckResponse.FromString,
                _registered_method=True)
        self.SyncUpdates = channel.unary_unary(
                '/replication.NodeService/SyncUpdates',
                request_serializer=src_dot_proto_dot_replication__pb2.UpdateGroup.SerializeToString,
                response_deserializer=src_dot_proto_dot_replication__pb2.AckResponse.FromString,
                _registered_method=True)
        self.NotifyLayerSync = channel.unary_unary(
                '/replication.NodeService/NotifyLayerSync',
                request_serializer=src_dot_proto_dot_replication__pb2.LayerSyncNotification.SerializeToString,
                response_deserializer=src_dot_proto_dot_replication__pb2.AckResponse.FromString,
                _registered_method=True)
        self.GetNodeStatus = channel.unary_unary(
                '/replication.NodeService/GetNodeStatus',
                request_serializer=src_dot_proto_dot_replication__pb2.Empty.SerializeToString,
                response_deserializer=src_dot_proto_dot_replication__pb2.NodeStatus.FromString,
                _registered_method=True)


class NodeServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def ExecuteTransaction(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def PropagateUpdate(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SyncUpdates(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def NotifyLayerSync(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetNodeStatus(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_NodeServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'ExecuteTransaction': grpc.unary_unary_rpc_method_handler(
                    servicer.ExecuteTransaction,
                    request_deserializer=src_dot_proto_dot_replication__pb2.Transaction.FromString,
                    response_serializer=src_dot_proto_dot_replication__pb2.TransactionResponse.SerializeToString,
            ),
            'PropagateUpdate': grpc.unary_unary_rpc_method_handler(
                    servicer.PropagateUpdate,
                    request_deserializer=src_dot_proto_dot_replication__pb2.UpdateNotification.FromString,
                    response_serializer=src_dot_proto_dot_replication__pb2.AckResponse.SerializeToString,
            ),
            'SyncUpdates': grpc.unary_unary_rpc_method_handler(
                    servicer.SyncUpdates,
                    request_deserializer=src_dot_proto_dot_replication__pb2.UpdateGroup.FromString,
                    response_serializer=src_dot_proto_dot_replication__pb2.AckResponse.SerializeToString,
            ),
            'NotifyLayerSync': grpc.unary_unary_rpc_method_handler(
                    servicer.NotifyLayerSync,
                    request_deserializer=src_dot_proto_dot_replication__pb2.LayerSyncNotification.FromString,
                    response_serializer=src_dot_proto_dot_replication__pb2.AckResponse.SerializeToString,
            ),
            'GetNodeStatus': grpc.unary_unary_rpc_method_handler(
                    servicer.GetNodeStatus,
                    request_deserializer=src_dot_proto_dot_replication__pb2.Empty.FromString,
                    response_serializer=src_dot_proto_dot_replication__pb2.NodeStatus.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'replication.NodeService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('replication.NodeService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class NodeService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def ExecuteTransaction(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/replication.NodeService/ExecuteTransaction',
            src_dot_proto_dot_replication__pb2.Transaction.SerializeToString,
            src_dot_proto_dot_replication__pb2.TransactionResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def PropagateUpdate(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/replication.NodeService/PropagateUpdate',
            src_dot_proto_dot_replication__pb2.UpdateNotification.SerializeToString,
            src_dot_proto_dot_replication__pb2.AckResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def SyncUpdates(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/replication.NodeService/SyncUpdates',
            src_dot_proto_dot_replication__pb2.UpdateGroup.SerializeToString,
            src_dot_proto_dot_replication__pb2.AckResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def NotifyLayerSync(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/replication.NodeService/NotifyLayerSync',
            src_dot_proto_dot_replication__pb2.LayerSyncNotification.SerializeToString,
            src_dot_proto_dot_replication__pb2.AckResponse.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def GetNodeStatus(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/replication.NodeService/GetNodeStatus',
            src_dot_proto_dot_replication__pb2.Empty.SerializeToString,
            src_dot_proto_dot_replication__pb2.NodeStatus.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
