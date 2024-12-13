"""Unit tests for message handling"""
import pytest
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import ProcessGroup, ProcessType
from src.processes.base_process import BaseProcess

class TestMessage:
    """Test cases for message handling"""

    def test_message_creation(self):
        """Test basic message creation"""
        msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id="TEST1",
            timestamp=123,
            data={"test": "data"},
            receiver_id="TEST2"
        )
        assert msg.msg_type == MessageType.REQUEST
        assert msg.sender_id == "TEST1"
        assert msg.timestamp == 123
        assert msg.data == {"test": "data"}
        assert msg.receiver_id == "TEST2"

    def test_process_id(self):
        """Test ProcessId creation and validation"""
        pid = ProcessId(
            process_type=ProcessType.LIGHT.value,
            group=ProcessGroup.A.value,
            number=1
        )
        assert pid.process_type == ProcessType.LIGHT.value
        assert pid.group == ProcessGroup.A.value
        assert pid.number == 1

class TestMessageSerialization:
    """Test cases for message serialization/deserialization"""

    @pytest.fixture
    def test_process(self):
        """Create a test process for serialization testing"""
        return BaseProcess(
            process_id=ProcessId(
                process_type=ProcessType.LIGHT.value,
                group=ProcessGroup.A.value,
                number=1
            )
        )

    def test_serialization(self, test_process):
        """Test message serialization"""
        original_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id="TEST1",
            timestamp=123,
            data={"test": "data"},
            receiver_id="TEST2"
        )
        serialized = test_process._serialize_message(original_msg)
        assert isinstance(serialized, bytes)

    def test_deserialization(self, test_process):
        """Test message deserialization"""
        original_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id="TEST1",
            timestamp=123,
            data={"test": "data"},
            receiver_id="TEST2"
        )
        serialized = test_process._serialize_message(original_msg)
        deserialized = test_process._deserialize_message(serialized)

        assert deserialized.msg_type == original_msg.msg_type
        assert deserialized.sender_id == original_msg.sender_id
        assert deserialized.timestamp == original_msg.timestamp
        assert deserialized.data == original_msg.data
        assert deserialized.receiver_id == original_msg.receiver_id

    @pytest.mark.parametrize("msg_type,data", [
        (MessageType.REQUEST, None),
        (MessageType.REPLY, {"priority": 1}),
        (MessageType.RELEASE, [1, 2, 3]),
        (MessageType.TOKEN, {"token_id": "123"}),
        (MessageType.ACTION, {"command": "start"}),
    ])
    def test_different_message_types(self, test_process, msg_type, data):
        """Test serialization of different message types and data"""
        original_msg = Message(
            msg_type=msg_type,
            sender_id="TEST1",
            timestamp=123,
            data=data,
            receiver_id="TEST2"
        )
        serialized = test_process._serialize_message(original_msg)
        deserialized = test_process._deserialize_message(serialized)

        assert deserialized.msg_type == original_msg.msg_type
        assert deserialized.data == original_msg.data

    def test_invalid_serialization(self, test_process):
        """Test handling of invalid serialization data"""
        with pytest.raises(RuntimeError):
            test_process._deserialize_message(b"invalid data")

    def test_large_message(self, test_process):
        """Test handling of large messages"""
        large_data = {"data": "x" * 1000}  # Create a large message
        original_msg = Message(
            msg_type=MessageType.REQUEST,
            sender_id="TEST1",
            timestamp=123,
            data=large_data,
            receiver_id="TEST2"
        )
        serialized = test_process._serialize_message(original_msg)
        deserialized = test_process._deserialize_message(serialized)
        assert deserialized.data == large_data