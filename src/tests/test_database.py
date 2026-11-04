"""Tests for Storage implementations (TDD approach).

Task 2.1: Write tests for Storage using InMemoryStorage.
These tests will pass because InMemoryStorage already exists in database.py.
"""

import sys
sys.path.insert(0, '/home/blastmerder/Documents/projects/python/localX/src')

import asyncio
import pytest
from database import InMemoryStorage


@pytest.fixture(params=[10, 5, 2])
def storage(request):
    """Create fresh storage with given max_history for each test."""
    s = InMemoryStorage(max_history=request.param)
    asyncio.run(s.init())
    yield s
    asyncio.run(s.close())


async def test_init(storage: InMemoryStorage):
    """Test that init() is a no-op for in-memory storage."""
    assert storage._messages == []


async def test_save_adds_message(storage: InMemoryStorage):
    """Test that save adds a message to the queue."""
    await storage.save("alice", "Hello, World!")
    
    history = await storage.fetch_history(10)
    assert len(history) == 1
    assert history[0]["sender"] == "alice"
    assert history[0]["message"] == "Hello, World!"


async def test_save_updates_timestamp(storage: InMemoryStorage):
    """Test that timestamp is set correctly."""
    import time
    
    t1_monotonic = time.monotonic()
    await storage.save("bob", "Test message")
    
    history = await storage.fetch_history(1)
    assert history[0]["timestamp"] >= t1_monotonic, f"Expected >= {t1_monotonic}, got {history[0]['timestamp']}"


async def test_fetch_returns_latest_first(storage: InMemoryStorage):
    """Verify fetch_history returns newest messages first."""
    # Store some fixed number of messages (max 3 to avoid issues if we add 3 and max is less)
    for user, msg in [("alice", "First"), ("bob", "Second"), ("carol", "Third")]:
        await storage.save(user, msg)
    
    # Calculate how many messages can actually be stored given max_history
    actual_stored = min(storage.max_history, 3)
    
    history = await storage.fetch_history(10)
    
    assert len(history) == actual_stored, f"Expected {actual_stored} from fetch but got {len(history)}"
    # All returned messages should be in correct newest-first order
    if actual_stored >= 2:
        assert history[0]["sender"] == "carol"
    if actual_stored >= 3:
        assert history[1]["sender"] == "bob"


async def test_fetch_limits_results(storage: InMemoryStorage):
    """Verify limit parameter works correctly."""
    for user in ["a", "b", "c", "d"]:
        await storage.save(user, f"From {user}")
    
    history_1 = await storage.fetch_history(1)
    assert len(history_1) == 1
    assert history_1[0]["sender"] == "d"  # Newest
    
    history_2 = await storage.fetch_history(2)
    assert len(history_2) == 2


async def test_close(storage: InMemoryStorage):
    """Test that close() doesn't raise."""
    await storage.close()


async def test_max_history_enforced(storage: InMemoryStorage):
    """Verify messages are dropped when exceeding max_history."""
    for i in range(20):  # Add more than max_history messages
        await storage.save("user", f"Message {i}")
    
    history = await storage.fetch_history(storage.max_history * 2)
    # Should only see last max_history messages
    assert len(history) == storage.max_history, f"Expected {storage.max_history} but got {len(history)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
