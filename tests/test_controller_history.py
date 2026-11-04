"""Tests for ChatController.get_history using Storage interface."""

import asyncio
from pathlib import Path
from src.controller.core import ChatController
from src.controller.models import Message, UserInfo
from src.storage.memory import InMemoryStorage


async def test_get_history_returns_fetch_history_result():
    """get_history should call storage.fetch_history and return results."""
    # Set up storage with test messages
    storage = InMemoryStorage()
    await storage.init()
    
    # Add some test messages
    await storage.save("Alice", "Hello!", 1000)
    await storage.save("Bob", "Hi there", 1001)
    await storage.save("Alice", "How are you?", 1002)
    await storage.save("Charlie", "Good", 1003)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Get history with limit 5
    history = await controller.get_history(limit=5)
    
    # Should return list of (sender_id, text, timestamp) tuples
    assert isinstance(history, list)
    assert len(history) == 4
    
    # Check that it matches stored data
    assert history[0] == ("Alice", "Hello!", 1000)
    assert history[1] == ("Bob", "Hi there", 1001)
    assert history[2] == ("Alice", "How are you?", 1002)
    assert history[3] == ("Charlie", "Good", 1003)


async def test_get_history_with_limit():
    """get_history should respect the limit parameter."""
    storage = InMemoryStorage()
    await storage.init()
    
    # Add messages with sequential timestamps
    for i in range(20):
        await storage.save(f"User{i}", f"Message {i}", i * 10)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Get only last 3 messages
    history = await controller.get_history(limit=3)
    
    assert len(history) == 3
    # Check that we get exactly 3 messages
    assert len(history[0][1]) > 0  # Messages are not empty


async def test_get_history_with_zero_limit():
    """get_history with limit=0 passes to storage implementation.
    
    Note: InMemoryStorage treats limit=0 as "return all" (see storage/memory.py line 22)
    SqliteStorage treats limit=0 as fetch all (sees limit as falsy, returns all)
    """
    storage = InMemoryStorage()
    await storage.init()
    
    # Save some messages first
    await storage.save("Alice", "Hello!", 1000)
    await storage.save("Bob", "Hi there", 1001)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    history = await controller.get_history(limit=0)
    # InMemoryStorage: limit=0 means "return all" (falsy check in storage implementation)
    assert len(history) == 2


async def test_get_history_with_large_limit():
    """get_history with very large limit should return all messages."""
    storage = InMemoryStorage()
    await storage.init()
    
    for i in range(50):
        await storage.save(f"User{i % 10}", f"Msg {i}", i)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    history = await controller.get_history(limit=1000)
    
    # Should return all 50 messages
    assert len(history) == 50


async def test_get_history_returns_tuple_format():
    """get_history should return tuple (sender_id, text, timestamp)."""
    storage = InMemoryStorage()
    await storage.init()
    
    await storage.save("TestUser", "test message 123", 999)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    history = await controller.get_history(limit=10)
    
    # Check format of returned item
    assert len(history[0]) == 3  # tuple with 3 elements if history exists


async def test_get_history_with_none_storage():
    """get_history with no storage should return empty list."""
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=None,
    )
    
    # Should handle None storage gracefully (return empty list)
    history = await controller.get_history(limit=10)
    
    assert isinstance(history, list)
    assert len(history) == 0


async def test_get_history_async_context():
    """get_history should work in async context properly."""
    storage = InMemoryStorage()
    await storage.init()
    
    for i in range(5):
        await storage.save(f"User{i}", f"Msg {i}", i * 100)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Test in async block
    result = await asyncio.wait_for(controller.get_history(limit=3), timeout=5.0)
    assert len(result) == 3
    
    # Verify content
    last_sender = result[-1][0]
    assert isinstance(last_sender, str)


async def test_get_history_with_none_limit_returns_all():
    """get_history with limit=None returns all messages."""
    storage = InMemoryStorage()
    await storage.init()
    
    for i in range(15):
        await storage.save(f"User{i % 3}", f"Msg {i}", i)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # None limit means all messages
    history = await controller.get_history(limit=None)
    
    assert len(history) == 15


async def test_get_history_returns_empty_on_init():
    """get_history should return empty list for fresh storage."""
    storage = InMemoryStorage()
    await storage.init()
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    history = await controller.get_history(limit=10)
    assert len(history) == 0


async def test_get_history_with_negative_limit():
    """get_history with negative limit behavior depends on storage implementation.
    
    InMemoryStorage treats negative limits the same as positive - returns last N messages.
    This is handled by storage implementation, not controller.
    """
    storage = InMemoryStorage()
    await storage.init()
    
    for i in range(10):
        await storage.save("User", f"Msg {i}", i)
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Negative limit - behavior depends on storage implementation
    history = await controller.get_history(limit=-5)
    assert isinstance(history, list)


async def test_get_history_integration_with_save_message():
    """Integration test: save messages then fetch history."""
    storage = InMemoryStorage()
    await storage.init()
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Save some messages through controller (timestamp auto-generated)
    await controller.save_message("Hello", "Alice")
    await controller.save_message("World", "Bob")
    
    # Fetch should return them
    history = await controller.get_history(limit=10)
    
    assert len(history) == 2
    # Check structure: (sender, text, timestamp)
    assert history[0][0] == "Alice"
    assert history[0][1] == "Hello"
    assert isinstance(history[0][2], int)
