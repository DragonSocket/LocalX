"""Tests for ChatController.save_message using Storage interface.

TDD Phase 1: Define expected behavior with tests that will be made to pass.
"""

import pytest
import asyncio
import tempfile

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_save_message_saves_valid_message():
    """save_message should save a valid message to storage when provided."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    # Setup storage
    storage = InMemoryStorage()
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    msg = "Hello, world!"
    await controller.save_message(msg, sender="TestUser", timestamp=1000)
    
    # Verify message was saved
    history = await storage.fetch_history(limit=10)
    assert len(history) == 1
    assert history[0][0] == "TestUser"
    assert history[0][1] == msg
    assert history[0][2] == 1000


@pytest.mark.asyncio
async def test_save_message_returns_false_without_storage():
    """save_message should return False when no storage is configured."""
    
    from src.controller.core import ChatController
    

    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=None,
    )
    
    msg = "Hello!"
    result = await controller.save_message(msg, sender="TestUser", timestamp=0)
    
    assert result is False


@pytest.mark.asyncio
async def test_save_message_invalid_empty_string():
    """save_message should raise ValueError for empty message."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    with pytest.raises(ValueError, match="Message is empty"):
        await controller.save_message("", sender="TestUser", timestamp=0)


@pytest.mark.asyncio
async def test_save_message_invalid_null():
    """save_message should raise ValueError for None message."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    with pytest.raises(ValueError, match="Message must be a string"):
        await controller.save_message(None, sender="TestUser", timestamp=0)


@pytest.mark.asyncio
async def test_save_message_too_long():
    """save_message should raise ValueError for message > 100 chars."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    long_msg = "x" * 101
    with pytest.raises(ValueError, match="Message too long"):
        await controller.save_message(long_msg, sender="TestUser", timestamp=0)


@pytest.mark.asyncio
async def test_save_message_invalid_username():
    """save_message should handle invalid username gracefully."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Empty username should fail
    with pytest.raises(ValueError, match="Invalid username"):
        await controller.save_message("Valid message", sender="", timestamp=0)
    
    # None username should fail
    with pytest.raises(ValueError, match="Invalid username"):
        await controller.save_message("Valid message", sender=None, timestamp=0)


@pytest.mark.asyncio
async def test_save_message_uses_storage_protocol():
    """save_message should use the Storage interface correctly."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Save multiple messages
    await controller.save_message("Message 1", sender="Alice", timestamp=100)
    await controller.save_message("Message 2", sender="Bob", timestamp=200)
    await controller.save_message("Message 3", sender="Charlie", timestamp=300)
    
    # Verify all saved in order
    history = await storage.fetch_history(limit=10)
    assert len(history) == 3
    assert history[0] == ("Alice", "Message 1", 100)
    assert history[1] == ("Bob", "Message 2", 200)
    assert history[2] == ("Charlie", "Message 3", 300)


@pytest.mark.asyncio
async def test_save_message_with_sqlite_storage():
    """save_message should work with SqliteStorage."""
    
    from src.storage.sqlite import SqliteStorage
    from src.controller.core import ChatController
    
    # Create temporary database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/chat.db"
        
        storage = SqliteStorage(db_path)
        await storage.init()
        
        controller = ChatController(
            name="TestUser",
            host="localhost",
            port=12345,
            storage=storage,
            transport=None,
        )
        
        msg = "Test SQLite save"
        result = await controller.save_message(msg, sender="Admin", timestamp=999)
        
        assert result is True
        
        # Verify in database through fetch_history
        history = await storage.fetch_history(limit=10)
        assert len(history) == 1
        assert history[0] == ("Admin", msg, 999)


@pytest.mark.asyncio
async def test_save_message_invalid_control_chars():
    """save_message should reject messages with invalid control characters."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Unicode control characters (null, VT, FF) should fail
    invalid_msg = "Hello\x00world"  # null byte
    with pytest.raises(ValueError):
        await controller.save_message(invalid_msg, sender="TestUser", timestamp=0)


@pytest.mark.asyncio
async def test_save_message_only_whitespace():
    """save_message should reject messages containing only whitespace."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    whitespace_msg = "   \n\t   "
    with pytest.raises(ValueError):
        await controller.save_message(whitespace_msg, sender="TestUser", timestamp=0)


@pytest.mark.asyncio
async def test_save_message_integration_with_state_manager():
    """save_message should integrate properly with StateManager."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Save a message - should update state_manager and save to storage
    await controller.save_message("Integration test", sender="ModAdmin", timestamp=0)
    
    # Verify in storage
    history = await storage.fetch_history(limit=10)
    assert len(history) == 1


@pytest.mark.asyncio
async def test_save_message_with_auto_timestamp():
    """save_message should auto-generate timestamp when not provided (for testing)."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    import time
    
    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Save with None timestamp - should use current time
    await controller.save_message("Timestamp test", sender="Tester", timestamp=None)
    
    history = await storage.fetch_history(limit=10)
    assert len(history) == 1
    # Timestamp should be auto-generated
    assert isinstance(history[0][2], int)


@pytest.mark.asyncio
async def test_save_message_special_characters():
    """save_message should handle special characters correctly."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    # Special chars that should be allowed (will be escaped by formatter on send)
    special_msg = "Hello!\nWorld.\tTabbed.<>HTML & Entities"
    await controller.save_message(special_msg, sender="Special", timestamp=0)
    
    history = await storage.fetch_history(limit=10)
    assert len(history) == 1
    assert "Hello!" in history[0][1]


@pytest.mark.asyncio
async def test_save_message_preserves_original_content():
    """save_message should preserve original message content exactly."""
    
    from src.storage.memory import InMemoryStorage
    from src.controller.core import ChatController
    

    storage = InMemoryStorage()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=storage,
        transport=None,
    )
    
    original = "<script>evil()</script>"  # HTML injection attempt
    await controller.save_message(original, sender="Injection", timestamp=0)
    
    history = await storage.fetch_history(limit=10)
    assert len(history) == 1
    # Content should be stored as-is (escaping happens on send to network)
    assert "<script>" in history[0][1]

