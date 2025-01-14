# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: src/proto/replication.proto
# Protobuf Python Version: 5.28.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    28,
    1,
    '',
    'src/proto/replication.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1bsrc/proto/replication.proto\x12\x0breplication\"\x07\n\x05\x45mpty\"J\n\x08\x44\x61taItem\x12\x0b\n\x03key\x18\x01 \x01(\x05\x12\r\n\x05value\x18\x02 \x01(\x05\x12\x0f\n\x07version\x18\x03 \x01(\x05\x12\x11\n\ttimestamp\x18\x04 \x01(\x03\"\x9f\x01\n\x0bTransaction\x12+\n\x04type\x18\x01 \x01(\x0e\x32\x1d.replication.Transaction.Type\x12\x14\n\x0ctarget_layer\x18\x02 \x01(\x05\x12*\n\noperations\x18\x03 \x03(\x0b\x32\x16.replication.Operation\"!\n\x04Type\x12\r\n\tREAD_ONLY\x10\x00\x12\n\n\x06UPDATE\x10\x01\"r\n\tOperation\x12,\n\x05write\x18\x01 \x01(\x0b\x32\x1b.replication.WriteOperationH\x00\x12*\n\x04read\x18\x02 \x01(\x0b\x32\x1a.replication.ReadOperationH\x00\x42\x0b\n\toperation\",\n\x0eWriteOperation\x12\x0b\n\x03key\x18\x01 \x01(\x05\x12\r\n\x05value\x18\x02 \x01(\x05\"\x1c\n\rReadOperation\x12\x0b\n\x03key\x18\x01 \x01(\x05\"N\n\x12UpdateNotification\x12#\n\x04\x64\x61ta\x18\x01 \x01(\x0b\x32\x15.replication.DataItem\x12\x13\n\x0bsource_node\x18\x02 \x01(\t\"o\n\x0bUpdateGroup\x12&\n\x07updates\x18\x01 \x03(\x0b\x32\x15.replication.DataItem\x12\x13\n\x0bsource_node\x18\x02 \x01(\t\x12\r\n\x05layer\x18\x03 \x01(\x05\x12\x14\n\x0cupdate_count\x18\x04 \x01(\x05\"\xae\x01\n\x15LayerSyncNotification\x12\x14\n\x0csource_layer\x18\x01 \x01(\x05\x12\x14\n\x0ctarget_layer\x18\x02 \x01(\x05\x12&\n\x07updates\x18\x03 \x03(\x0b\x32\x15.replication.DataItem\x12\x14\n\x0cupdate_count\x18\x04 \x01(\x05\x12\x16\n\x0esync_timestamp\x18\x05 \x01(\x03\x12\x13\n\x0bsource_node\x18\x06 \x01(\t\"/\n\x0b\x41\x63kResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"e\n\x13TransactionResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12&\n\x07results\x18\x02 \x03(\x0b\x32\x15.replication.DataItem\x12\x15\n\rerror_message\x18\x03 \x01(\t\"o\n\nNodeStatus\x12\x0f\n\x07node_id\x18\x01 \x01(\t\x12\r\n\x05layer\x18\x02 \x01(\x05\x12\x14\n\x0cupdate_count\x18\x03 \x01(\x05\x12+\n\x0c\x63urrent_data\x18\x04 \x03(\x0b\x32\x15.replication.DataItem\"6\n\rUpdateRequest\x12%\n\x06update\x18\x01 \x01(\x0b\x32\x15.replication.DataItem2\x89\x03\n\x0bNodeService\x12R\n\x12\x45xecuteTransaction\x12\x18.replication.Transaction\x1a .replication.TransactionResponse\"\x00\x12N\n\x0fPropagateUpdate\x12\x1f.replication.UpdateNotification\x1a\x18.replication.AckResponse\"\x00\x12\x43\n\x0bSyncUpdates\x12\x18.replication.UpdateGroup\x1a\x18.replication.AckResponse\"\x00\x12Q\n\x0fNotifyLayerSync\x12\".replication.LayerSyncNotification\x1a\x18.replication.AckResponse\"\x00\x12>\n\rGetNodeStatus\x12\x12.replication.Empty\x1a\x17.replication.NodeStatus\"\x00\x62\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'src.proto.replication_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_EMPTY']._serialized_start=44
  _globals['_EMPTY']._serialized_end=51
  _globals['_DATAITEM']._serialized_start=53
  _globals['_DATAITEM']._serialized_end=127
  _globals['_TRANSACTION']._serialized_start=130
  _globals['_TRANSACTION']._serialized_end=289
  _globals['_TRANSACTION_TYPE']._serialized_start=256
  _globals['_TRANSACTION_TYPE']._serialized_end=289
  _globals['_OPERATION']._serialized_start=291
  _globals['_OPERATION']._serialized_end=405
  _globals['_WRITEOPERATION']._serialized_start=407
  _globals['_WRITEOPERATION']._serialized_end=451
  _globals['_READOPERATION']._serialized_start=453
  _globals['_READOPERATION']._serialized_end=481
  _globals['_UPDATENOTIFICATION']._serialized_start=483
  _globals['_UPDATENOTIFICATION']._serialized_end=561
  _globals['_UPDATEGROUP']._serialized_start=563
  _globals['_UPDATEGROUP']._serialized_end=674
  _globals['_LAYERSYNCNOTIFICATION']._serialized_start=677
  _globals['_LAYERSYNCNOTIFICATION']._serialized_end=851
  _globals['_ACKRESPONSE']._serialized_start=853
  _globals['_ACKRESPONSE']._serialized_end=900
  _globals['_TRANSACTIONRESPONSE']._serialized_start=902
  _globals['_TRANSACTIONRESPONSE']._serialized_end=1003
  _globals['_NODESTATUS']._serialized_start=1005
  _globals['_NODESTATUS']._serialized_end=1116
  _globals['_UPDATEREQUEST']._serialized_start=1118
  _globals['_UPDATEREQUEST']._serialized_end=1172
  _globals['_NODESERVICE']._serialized_start=1175
  _globals['_NODESERVICE']._serialized_end=1568
# @@protoc_insertion_point(module_scope)