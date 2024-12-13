"""Unit tests for logical clock implementations"""
import pytest
from src.algorithms.lamport_clock import LamportClock
from src.algorithms.vector_clock import VectorClock

class TestLamportClock:
    """Test cases for Lamport's logical clock"""

    def test_initialization(self):
        """Test clock initialization"""
        clock = LamportClock()
        assert clock.get_timestamp() == 0

    def test_increment(self):
        """Test clock increment"""
        clock = LamportClock()
        clock.increment()
        assert clock.get_timestamp() == 1

    def test_update(self):
        """Test clock update with received timestamp"""
        clock = LamportClock()
        clock.increment()  # timestamp = 1
        clock.update(3)   # should set to max(1,3) + 1 = 4
        assert clock.get_timestamp() == 4

    def test_multiple_updates(self):
        """Test multiple clock updates"""
        clock = LamportClock()
        clock.increment()  # 1
        clock.update(3)   # 4
        clock.increment() # 5
        clock.update(2)   # should stay at 5 + 1 = 6
        assert clock.get_timestamp() == 6

    @pytest.mark.parametrize("my_ts,other_ts,my_id,other_id,expected", [
        (1, 2, "A1", "A2", True),   # Lower timestamp wins
        (2, 1, "A1", "A2", False),  # Higher timestamp loses
        (1, 1, "A1", "A2", True),   # Equal timestamps, lower ID wins
        (1, 1, "A2", "A1", False),  # Equal timestamps, higher ID loses
    ])
    def test_comparison(self, my_ts, other_ts, my_id, other_id, expected):
        """Test clock comparison for mutual exclusion"""
        clock = LamportClock()
        clock.timestamp = my_ts
        assert clock.compare(other_ts, other_id, my_id) == expected

class TestVectorClock:
    """Test cases for Vector Clock implementation"""

    def test_initialization(self):
        """Test clock initialization"""
        clock = VectorClock(process_id="0", num_processes=3)
        assert clock.get_timestamp() == {"0": 0, "1": 0, "2": 0}
        assert clock.process_id == "0"

    def test_increment(self):
        """Test clock increment"""
        clock = VectorClock(process_id="1", num_processes=3)
        clock.increment()
        timestamps = clock.get_timestamp()
        assert timestamps["1"] == 1  # Own process incremented
        assert timestamps["0"] == 0  # Others unchanged
        assert timestamps["2"] == 0  # Others unchanged

    def test_update(self):
        """Test clock update with received vector"""
        clock = VectorClock(process_id="0", num_processes=3)
        clock.increment()  # [1,0,0]
        received = {"0": 0, "1": 2, "2": 1}
        clock.update(received)  # Should become [2,2,1]
        timestamps = clock.get_timestamp()
        assert timestamps["0"] == 2
        assert timestamps["1"] == 2
        assert timestamps["2"] == 1

    @pytest.mark.parametrize("my_vector,other_vector,my_id,other_id,expected", [
        ({"0": 1, "1": 0}, {"0": 0, "1": 2}, "0", "1", True),    # Lower timestamp wins (1 < 2)
        ({"0": 1, "1": 0}, {"0": 0, "1": 0}, "0", "1", False),   # Higher timestamp loses (1 > 0)
        ({"0": 1, "1": 1}, {"0": 1, "1": 1}, "0", "1", True),    # Equal timestamps, lower ID wins
        ({"0": 1, "1": 1}, {"0": 1, "1": 1}, "1", "0", False),   # Equal timestamps, higher ID loses
    ])
    def test_comparison(self, my_vector, other_vector, my_id, other_id, expected):
        """Test clock comparison for Ricart-Agrawala algorithm"""
        clock = VectorClock(process_id=my_id, num_processes=2)
        clock.vector = my_vector.copy()
        assert clock.compare(other_vector, other_id) == expected

    def test_vector_independence(self):
        """Test that vector timestamps are independent"""
        clock = VectorClock(process_id="0", num_processes=2)
        ts1 = clock.get_timestamp()
        ts1["0"] = 5  # Modify the copy
        ts2 = clock.get_timestamp()
        assert ts2["0"] == 0  # Original should be unchanged

class TestVectorClockErrors:
    """Error handling test cases for Vector Clock"""

    def test_invalid_process_id(self):
        """Test handling of invalid process IDs"""
        with pytest.raises(ValueError, match="Invalid process ID"):
            VectorClock(process_id="3", num_processes=3)

    def test_invalid_num_processes(self):
        """Test handling of invalid number of processes"""
        with pytest.raises(ValueError, match="Number of processes must be positive"):
            VectorClock(process_id="0", num_processes=0)

    def test_malformed_vector(self):
        """Test handling of malformed vector timestamps"""
        clock = VectorClock(process_id="0", num_processes=2)
        with pytest.raises(ValueError, match="Invalid vector timestamp: values must be numeric"):
            clock.update({"0": "invalid"})

    def test_missing_process_id(self):
        """Test handling of missing process ID in vector"""
        clock = VectorClock(process_id="0", num_processes=2)
        with pytest.raises(KeyError, match="Missing process ID in vector"):
            clock.compare({"0": 0}, "1")  # Missing process ID "1" in vector

    def test_negative_timestamp(self):
        """Test handling of negative timestamps"""
        clock = VectorClock(process_id="0", num_processes=2)
        with pytest.raises(ValueError, match="Timestamps must be non-negative"):
            clock.update({"0": -1, "1": 0})

class TestClockEdgeCases:
    """Edge case test cases for Vector Clock"""

    def test_single_process(self):
        """Test vector clock with single process"""
        clock = VectorClock(process_id="0", num_processes=1)
        clock.increment()
        assert clock.get_timestamp() == {"0": 1}

    def test_max_processes(self):
        """Test vector clock with maximum allowed processes"""
        max_processes = 1000  # Adjust based on system limits
        clock = VectorClock(process_id="0", num_processes=max_processes)
        assert len(clock.get_timestamp()) == max_processes

    def test_zero_timestamps(self):
        """Test comparison with zero timestamps"""
        clock = VectorClock(process_id="0", num_processes=2)
        other_vector = {"0": 0, "1": 0}
        assert clock.compare(other_vector, "1") == True  # Lower ID wins

    @pytest.mark.parametrize("timestamp", [
        2**31 - 1,  # Max 32-bit int
        2**63 - 1,  # Max 64-bit int
    ])
    def test_large_timestamps(self, timestamp):
        """Test handling of large timestamp values"""
        clock = VectorClock(process_id="0", num_processes=2)
        clock.vector["0"] = timestamp
        clock.increment()
        assert clock.vector["0"] == timestamp + 1

    def test_concurrent_events(self):
        """Test handling of concurrent events"""
        clock1 = VectorClock(process_id="0", num_processes=3)
        clock2 = VectorClock(process_id="1", num_processes=3)
        clock3 = VectorClock(process_id="2", num_processes=3)

        # Simulate concurrent events
        clock1.increment()  # [1,0,0]
        clock2.increment()  # [0,1,0]
        clock3.increment()  # [0,0,1]

        # Update clock1 with clock2's time
        clock1.update(clock2.get_timestamp())  # Should be [2,1,0]
        assert clock1.vector["0"] == 2
        assert clock1.vector["1"] == 1
        assert clock1.vector["2"] == 0

        # Update clock1 with clock3's time
        clock1.update(clock3.get_timestamp())  # Should be [3,1,1]
        assert clock1.vector["0"] == 3
        assert clock1.vector["1"] == 1
        assert clock1.vector["2"] == 1