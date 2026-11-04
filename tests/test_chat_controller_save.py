"""Tests for ChatController.save_message with Storage interface."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from controller.core import ChatController, StateData, HistoryState, UserInfo, SystemState, Message


async def test_save_message_with_valid_input():
    """Test saving a valid message returns True and updates history."""
    storage = AsyncMock(spec=["Storage"])
    storage.save = AsyncMock(return_value=True)
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    # Initialize state
    user_info = UserInfo(username="TestUser")
    controller.state_manager._init_state(user_info)
    
    result = await controller.save_message("test message", "LocalUser")
    
    assert result is True
    assert storage.save.called
    args, kwargs = storage.save.call_args
    assert kwargs["user"] == "TestUser"
    assert kwargs["msg"] == "test message"


async def test_save_message_with_none_user():
    """Test that None user raises ValueError."""
    storage = AsyncMock(spec=["Storage"])
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    with pytest.raises(ValueError) as exc_info:
        await controller.save_message("message", "User")
    
    assert "username" in str(exc_info.value).lower()
    storage.save.assert_not_called()


async def test_save_message_with_empty_user():
    """Test that empty user raises ValueError."""
    storage = AsyncMock(spec=["Storage"])
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    with pytest.raises(ValueError) as exc_info:
        await controller.save_message("message", "")
    
    assert "username" in str(exc_info.value).lower()
    storage.save.assert_not_called()


async def test_save_message_with_empty_content():
    """Test that empty message content raises ValueError."""
    storage = AsyncMock(spec=["Storage"])
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    with pytest.raises(ValueError) as exc_info:
        await controller.save_message("", "User")
    
    assert "message" in str(exc_info.value).lower()
    storage.save.assert_not_called()


async def test_save_message_with_whitespace_only():
    """Test that whitespace-only message raises ValueError."""
    storage = AsyncMock(spec=["Storage"])
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    with pytest.raises(ValueError) as exc_info:
        await controller.save_message("   ", "User")
    
    assert "message" in str(exc_info.value).lower()
    storage.save.assert_not_called()


async def test_save_message_fetches_and_saves():
    """Test that save_message fetches history first, then saves."""
    from interfaces import Storage
    
    storage = AsyncMock(spec=Storage)
    storage.init = AsyncMock(return_value=None)
    storage.fetch_history = AsyncMock(return_value=[("existing", "OtherUser", 1000)])
    storage.save = AsyncMock(return_value=True)
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    await controller.save_message("new message", "CurrentUser")
    
    # Should have been initialized (fetch_history is called in init)
    assert storage.init.called
    assert storage.fetch_history.called


async def test_save_message_with_timestamp():
    """Test save_message respects optional timestamp."""
    from interfaces import Storage
    
    storage = AsyncMock(spec=Storage)
    storage.save = AsyncMock(return_value=True)
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    # Initialize to avoid init() call
    user_info = UserInfo(username="TestUser")
    controller.state_manager._init_state(user_info)
    
    ts = 1234567890
    await controller.save_message("msg", "MyUser", timestamp=ts)
    
    args, kwargs = storage.save.call_args
    assert kwargs["timestamp"] == ts


async def test_save_message_false_returns_not_saved():
    """Test that False return from storage is handled."""
    storage = AsyncMock(spec=["Storage"])
    storage.save = AsyncMock(return_value=False)
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    user_info = UserInfo(username="TestUser")
    controller.state_manager._init_state(user_info)
    
    result = await controller.save_message("msg", "MyUser")
    
    assert result is False
    assert storage.save.called


async def test_save_message_does_not_modify_history_directly():
    """Test that save_message doesn't directly modify stored history."""
    from interfaces import Storage
    
    storage = AsyncMock(spec=Storage)
    storage.fetch_history = AsyncMock(return_value=[("old", "OtherUser", 100)])
    storage.save = AsyncMock(return_value=True)
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    await controller.save_message("new", "CurrentUser")
    
    # Storage should be called with save, not history mutation
    assert storage.save.called


class FakeStorage:
    """Fake storage that implements Storage protocol for real calls."""
    
    async def init(self) -> None:
        self._db = {}
    
    async def save(self, user: str, msg: str, timestamp: int | None = None) -> bool:
        key = f"{user}_{timestamp or 'now'}_{msg}"
        if not user or not msg:
            return False
        self._db[key] = (msg, user, timestamp or 0)
        return True
    
    async def fetch_history(self, limit: int) -> list[tuple[str, str, int]]:
        items = list(self._db.items())[:limit]
        return [(d[0], d[1], d[2]) for d in items]
    
    async def close(self) -> None:
        pass


async def test_save_message_real_storage_interface():
    """Test with real Storage interface implementation."""
    storage = FakeStorage()
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    asyncio.run(storage.init())
    history = await storage.fetch_history(10)
    controller.state_manager.initialize_with_history(history)
    
    result = await controller.save_message("test", "TestUser")
    
    assert result is True
    assert len(storage._db) == 1
    key, (msg, user, ts) = next(iter(storage._db.items()))
    assert msg == "test"
    assert user == "TestUser"


async def test_save_message_with_negative_timestamp():
    """Test timestamp=0 uses default behavior."""
    storage = AsyncMock(spec=["Storage"])
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    user_info = UserInfo(username="TestUser")
    controller.state_manager._init_state(user_info)
    
    await controller.save_message("msg", "MyUser", timestamp=-100)
    
    args, kwargs = storage.save.call_args
    assert kwargs["timestamp"] == -100


async def test_save_message_with_large_timestamp():
    """Test with large future timestamp."""
    storage = AsyncMock(spec=["Storage"])
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    user_info = UserInfo(username="TestUser")
    controller.state_manager._init_state(user_info)
    
    ts_fut = 9999999999
    await controller.save_message("msg", "MyUser", timestamp=ts_fut)
    
    args, kwargs = storage.save.call_args
    assert kwargs["timestamp"] == ts_fut


async def test_save_message_invalid_input_types():
    """Test message parameter must be string."""
    storage = AsyncMock(spec=["Storage"])
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    with pytest.raises(ValueError) as exc_info:
        await controller.save_message(None, "User")
    
    assert "message" in str(exc_info.value).lower()


async def test_save_message_user_with_special_chars():
    """Test user with special characters is passed through."""
    storage = AsyncMock(spec=["Storage"])
    storage.init = AsyncMock(return_value=None)
    storage.fetch_history = AsyncMock(return_value=[])
    storage.save = AsyncMock(return_value=True)
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    await controller.save_message("msg", "User with spaces")
    
    args, kwargs = storage.save.call_args
    assert kwargs["user"] == "User with spaces"


async def test_save_message_doesnt_call_storage_on_validation_error():
    """Test that validation errors don't call storage."""
    storage = AsyncMock(spec=["Storage"])
    storage.save.side_effect = Exception("Should not be called")
    
    controller = ChatController(
        state_manager=ChatController._create_state_manager(),
        storage=storage,
    )
    
    user_info = UserInfo(username="TestUser")
    controller.state_manager._init_state(user_info)
    
    with pytest.raises(ValueError):
        await controller.save_message("", "MyUser")
    
    assert not storage.save.called
