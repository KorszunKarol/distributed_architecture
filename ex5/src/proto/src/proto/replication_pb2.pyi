from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DataItem(_message.Message):
    __slots__ = ("key", "value", "version", "timestamp")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    key: int
    value: int
    version: int
    timestamp: int
    def __init__(self, key: _Optional[int] = ..., value: _Optional[int] = ..., version: _Optional[int] = ..., timestamp: _Optional[int] = ...) -> None: ...

class Transaction(_message.Message):
    __slots__ = ("type", "target_layer", "operations")
    class Type(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        READ_ONLY: _ClassVar[Transaction.Type]
        UPDATE: _ClassVar[Transaction.Type]
    READ_ONLY: Transaction.Type
    UPDATE: Transaction.Type
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TARGET_LAYER_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    type: Transaction.Type
    target_layer: int
    operations: _containers.RepeatedCompositeFieldContainer[Operation]
    def __init__(self, type: _Optional[_Union[Transaction.Type, str]] = ..., target_layer: _Optional[int] = ..., operations: _Optional[_Iterable[_Union[Operation, _Mapping]]] = ...) -> None: ...

class Operation(_message.Message):
    __slots__ = ("write", "read")
    WRITE_FIELD_NUMBER: _ClassVar[int]
    READ_FIELD_NUMBER: _ClassVar[int]
    write: WriteOperation
    read: ReadOperation
    def __init__(self, write: _Optional[_Union[WriteOperation, _Mapping]] = ..., read: _Optional[_Union[ReadOperation, _Mapping]] = ...) -> None: ...

class WriteOperation(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: int
    value: int
    def __init__(self, key: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class ReadOperation(_message.Message):
    __slots__ = ("key",)
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: int
    def __init__(self, key: _Optional[int] = ...) -> None: ...

class UpdateNotification(_message.Message):
    __slots__ = ("data", "source_node")
    DATA_FIELD_NUMBER: _ClassVar[int]
    SOURCE_NODE_FIELD_NUMBER: _ClassVar[int]
    data: DataItem
    source_node: str
    def __init__(self, data: _Optional[_Union[DataItem, _Mapping]] = ..., source_node: _Optional[str] = ...) -> None: ...

class UpdateGroup(_message.Message):
    __slots__ = ("updates", "source_node", "layer", "update_count")
    UPDATES_FIELD_NUMBER: _ClassVar[int]
    SOURCE_NODE_FIELD_NUMBER: _ClassVar[int]
    LAYER_FIELD_NUMBER: _ClassVar[int]
    UPDATE_COUNT_FIELD_NUMBER: _ClassVar[int]
    updates: _containers.RepeatedCompositeFieldContainer[DataItem]
    source_node: str
    layer: int
    update_count: int
    def __init__(self, updates: _Optional[_Iterable[_Union[DataItem, _Mapping]]] = ..., source_node: _Optional[str] = ..., layer: _Optional[int] = ..., update_count: _Optional[int] = ...) -> None: ...

class LayerSyncNotification(_message.Message):
    __slots__ = ("source_layer", "target_layer", "updates", "update_count", "sync_timestamp", "source_node")
    SOURCE_LAYER_FIELD_NUMBER: _ClassVar[int]
    TARGET_LAYER_FIELD_NUMBER: _ClassVar[int]
    UPDATES_FIELD_NUMBER: _ClassVar[int]
    UPDATE_COUNT_FIELD_NUMBER: _ClassVar[int]
    SYNC_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    SOURCE_NODE_FIELD_NUMBER: _ClassVar[int]
    source_layer: int
    target_layer: int
    updates: _containers.RepeatedCompositeFieldContainer[DataItem]
    update_count: int
    sync_timestamp: int
    source_node: str
    def __init__(self, source_layer: _Optional[int] = ..., target_layer: _Optional[int] = ..., updates: _Optional[_Iterable[_Union[DataItem, _Mapping]]] = ..., update_count: _Optional[int] = ..., sync_timestamp: _Optional[int] = ..., source_node: _Optional[str] = ...) -> None: ...

class AckResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class TransactionResponse(_message.Message):
    __slots__ = ("success", "results", "error_message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    results: _containers.RepeatedCompositeFieldContainer[DataItem]
    error_message: str
    def __init__(self, success: bool = ..., results: _Optional[_Iterable[_Union[DataItem, _Mapping]]] = ..., error_message: _Optional[str] = ...) -> None: ...

class NodeStatus(_message.Message):
    __slots__ = ("node_id", "layer", "update_count", "current_data")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    LAYER_FIELD_NUMBER: _ClassVar[int]
    UPDATE_COUNT_FIELD_NUMBER: _ClassVar[int]
    CURRENT_DATA_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    layer: int
    update_count: int
    current_data: _containers.RepeatedCompositeFieldContainer[DataItem]
    def __init__(self, node_id: _Optional[str] = ..., layer: _Optional[int] = ..., update_count: _Optional[int] = ..., current_data: _Optional[_Iterable[_Union[DataItem, _Mapping]]] = ...) -> None: ...

class UpdateRequest(_message.Message):
    __slots__ = ("update",)
    UPDATE_FIELD_NUMBER: _ClassVar[int]
    update: DataItem
    def __init__(self, update: _Optional[_Union[DataItem, _Mapping]] = ...) -> None: ...
