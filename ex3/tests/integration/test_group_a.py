"""Integration tests for Group A's Lamport algorithm implementation"""
import pytest
import asyncio
from src.processes.lightweight_a import LightweightProcessA
from src.common.message import Message, MessageType, ProcessId
from src.common.constants import ProcessGroup, ProcessType, NetworkConfig

@pytest.fixture
async def processes(unused_tcp_port_factory):
    """Create a set of test processes"""
    procs = []
    for i in range(1, NetworkConfig.NUM_LIGHTWEIGHT_PROCESSES + 1):
        port = unused_tcp_port_factory()
        proc = LightweightProcessA(
            process_id=ProcessId(
                process_type=ProcessType.LIGHT.value,
                group=ProcessGroup.A.value,
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
async def test_request_ordering(processes):
    """Test that requests are ordered correctly using Lamport's algorithm"""
    # Simulate concurrent requests from all processes
    requests = []
    for proc in processes:
        proc.clock.timestamp = 0  # Reset clocks
        proc.clock.increment()
        request = Message(
            msg_type=MessageType.REQUEST,
            sender_id=f"LWA{proc.number}",
            timestamp=proc.clock.get_timestamp(),
            receiver_id="TEST"
        )
        requests.append((proc, request))

    # Collect timestamps and verify ordering
    timestamps = [(req.timestamp, req.sender_id) for _, req in requests]
    timestamps.sort()

    # Verify that timestamps are unique
    assert len(set(timestamps)) == len(timestamps)

@pytest.mark.asyncio
async def test_message_handling(processes):
    """Test message handling between processes"""
    proc1, proc2 = processes[:2]

    # Send request from proc1 to proc2
    request_msg = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWA{proc1.number}",
        timestamp=proc1.clock.get_timestamp(),
        receiver_id=f"LWA{proc2.number}"
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
    except asyncio.TimeoutError:
        pytest.fail("Message receiving timed out")

@pytest.mark.asyncio
async def test_clock_synchronization(processes):
    """Test that Lamport clocks maintain causal ordering"""
    proc1, proc2 = processes[:2]

    # Initial timestamps
    proc1.clock.increment()  # ts = 1
    ts1 = proc1.clock.get_timestamp()

    # Send message from proc1 to proc2
    msg = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWA{proc1.number}",
        timestamp=ts1,
        receiver_id=f"LWA{proc2.number}"
    )

    # Receive and update proc2's clock
    proc2.clock.update(msg.timestamp)
    ts2 = proc2.clock.get_timestamp()

    # Verify causal ordering
    assert ts2 > ts1, "Causal ordering violated"

@pytest.mark.asyncio
async def test_concurrent_requests(processes):
    """Test handling of concurrent requests"""
    proc1, proc2 = processes[:2]

    # Both processes request CS simultaneously
    proc1.requesting_cs = True
    proc2.requesting_cs = True

    # Create timestamps
    proc1.clock.increment()
    proc2.clock.increment()
    ts1 = proc1.clock.get_timestamp()
    ts2 = proc2.clock.get_timestamp()

    # Create requests
    req1 = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWA{proc1.number}",
        timestamp=ts1,
        receiver_id=f"LWA{proc2.number}"
    )

    req2 = Message(
        msg_type=MessageType.REQUEST,
        sender_id=f"LWA{proc2.number}",
        timestamp=ts2,
        receiver_id=f"LWA{proc1.number}"
    )

    # Verify that the requests are ordered correctly
    if ts1 < ts2 or (ts1 == ts2 and proc1.number < proc2.number):
        assert proc1.clock.compare(ts2, req2.sender_id, req1.sender_id)
    else:
        assert proc2.clock.compare(ts1, req1.sender_id, req2.sender_id)