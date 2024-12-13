"""Integration tests for Group B's Ricart-Agrawala algorithm implementation"""
import pytest
import asyncio
from src.processes.lightweight_b import LightweightProcessB
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import ProcessGroup, ProcessType, NetworkConfig

@pytest.fixture
async def processes(unused_tcp_port_factory):
    """Create a set of test processes"""
    procs = []
    for i in range(1, NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES + 1):
        port = unused_tcp_port_factory()
        proc = LightweightProcessB(
            process_id=ProcessId(
                process_type=ProcessType.LIGHT.value,
                group=ProcessGroup.B.value,
                number=i
            ),
            number=i,
            port=port
        )
        procs.append(proc)
    yield procs
    # Cleanup
    for proc in procs:
        proc.cleanup()

@pytest.mark.asyncio
async def test_vector_clock_updates(processes):
    """Test that vector clocks are properly updated during communication"""
    proc1, proc2 = processes[:2]

    # Initial event in proc1
    proc1.clock.increment()
    vec1 = proc1.clock.get_timestamp()

    # Send message from proc1 to proc2
    msg = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWB{proc1.number}",
        timestamp=proc1.clock.get_timestamp(),
        data=vec1,
        receiver_id=f"LWB{proc2.number}"
    )

    # Update proc2's clock
    proc2.clock.update(vec1)
    vec2 = proc2.clock.get_timestamp()

    # Verify vector clock properties
    assert vec2[str(proc2.number - 1)] > vec1[str(proc2.number - 1)]
    for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
        if i != proc2.number - 1:
            assert vec2[str(i)] >= vec1[str(i)]

@pytest.mark.asyncio
async def test_message_handling(processes):
    """Test message handling between processes"""
    proc1, proc2 = processes[:2]

    # Prepare vector clock data
    proc1.clock.increment()
    vector_data = proc1.clock.get_timestamp()

    # Send request from proc1 to proc2
    request_msg = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWB{proc1.number}",
        timestamp=proc1.clock.get_timestamp(),
        data=vector_data,
        receiver_id=f"LWB{proc2.number}"
    )

    # Start proc2's receive task
    receive_task = asyncio.create_task(proc2.receive_message())
    await asyncio.sleep(0.1)  # Give the server time to start

    # Send message from proc1
    await proc1.send_message(request_msg, proc2.port)

    # Get received message
    try:
        received_msg = await asyncio.wait_for(receive_task, timeout=1.0)

        # Verify message contents
        assert received_msg.msg_type == request_msg.msg_type
        assert received_msg.sender_id == request_msg.sender_id
        assert received_msg.timestamp == request_msg.timestamp
        assert received_msg.data == vector_data
    except asyncio.TimeoutError:
        pytest.fail("Message receiving timed out")

@pytest.mark.asyncio
async def test_concurrent_requests(processes):
    """Test handling of concurrent requests with vector clocks"""
    proc1, proc2 = processes[:2]

    # Both processes request CS simultaneously
    proc1.requesting_cs = True
    proc2.requesting_cs = True

    # Create timestamps with vector clocks
    proc1.clock.increment()
    proc2.clock.increment()
    vec1 = proc1.clock.get_timestamp()
    vec2 = proc2.clock.get_timestamp()

    # Create requests
    req1 = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWB{proc1.number}",
        timestamp=proc1.clock.get_timestamp(),
        data=vec1,
        receiver_id=f"LWB{proc2.number}"
    )

    req2 = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWB{proc2.number}",
        timestamp=proc2.clock.get_timestamp(),
        data=vec2,
        receiver_id=f"LWB{proc1.number}"
    )

    # Verify Ricart-Agrawala ordering
    if proc1.clock.compare(vec2, str(proc2.number - 1)):
        assert not proc2.clock.compare(vec1, str(proc1.number - 1))
    else:
        assert proc2.clock.compare(vec1, str(proc1.number - 1))

@pytest.mark.asyncio
async def test_vector_clock_causality(processes):
    """Test that vector clocks maintain causality"""
    proc1, proc2, proc3 = processes

    # Event in proc1
    proc1.clock.increment()
    vec1 = proc1.clock.get_timestamp()

    # Send to proc2 and update
    proc2.clock.update(vec1)
    proc2.clock.increment()
    vec2 = proc2.clock.get_timestamp()

    # Send to proc3 and update
    proc3.clock.update(vec2)
    vec3 = proc3.clock.get_timestamp()

    # Verify causality
    for i in range(NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES):
        assert vec3[str(i)] >= vec2[str(i)] >= vec1[str(i)]