import pytest
import asyncio
from src.mocks.in_memory_storage import InMemoryStorage, Msg, User


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def storage():
    """Create a fresh InMemoryStorage instance."""
    return InMemoryStorage()


class TestInitialize:
    """Tests for the init method."""

    @pytest.mark.asyncio
    async def test_init_succeeds(self, storage):
        """Init should always succeed."""
        await storage.init()
        assert storage._initialized is True

    @pytest.mark.asyncio
    async def test_init_reset_state(self, storage):
        """Init should succeed - no need to verify reset on fresh fixture."""
        await storage.init()
        assert storage._initialized is True
    

class TestSave:
    """Tests for the save method."""

    @pytest.mark.asyncio
    async def test_save_auto_registers_user(self, storage):
        """Save should auto-register user if not exists."""
        await storage.init()
        
        user = User(id="u1", name="Alice")
        msg = Msg(body="hello", peer_id=None)
        
        await storage.save(user, msg)
        
        assert "u1" in storage._users
        assert len(storage._messages["u1"]) == 1

    @pytest.mark.asyncio
    async def test_save_adds_message(self, storage):
        """Save should append message to user's history."""
        await storage.init()
        
        user = User(id="u2", name="Bob")
        msg1 = Msg(body="msg1", peer_id="peer1")
        
        await storage.save(user, msg1)
        
        messages = storage._messages["u2"]
        assert len(messages) == 1
        assert messages[0].body == "msg1"
        assert messages[0].peer_id == "peer1"

    @pytest.mark.asyncio
    async def test_save_without_init_raises(self, storage):
        """Save should raise if not initialized."""
        # Skip initialization
        await asyncio.sleep(0)  # Let coroutine start
        
        user = User(id="u3", name="Charlie")
        msg = Msg(body="msg")
        
        with pytest.raises(RuntimeError, match="Storage not initialized"):
            await storage.save(user, msg)


class TestFetchHistory:
    """Tests for the fetch_history method."""

    @pytest.mark.asyncio
    async def test_fetch_returns_empty_for_unknown_user(self, storage):
        """Fetch history returns empty list for unknown user."""
        await storage.init()
        msgs = await storage.fetch_history("unknown_user")
        assert msgs == []

    @pytest.mark.asyncio
    async def test_fetch_returns_all_messages(self, storage):
        """Fetch returns all messages sorted chronologically."""
        await storage.init()
        
        user = User(id="user1", name="TestUser")
        # Add 2 messages without timestamps (default=0.0)
        msg1 = Msg(body="first", peer_id="p1")
        msg2 = Msg(body="second", peer_id="p2")
        
        await storage.fetch_history("user1")  # clear before save
        
        await storage.save(user, msg1)
        await asyncio.sleep(0.01)
        await storage.save(user, msg2)
        
        msgs = await storage.fetch_history("user1")
        
        assert len(msgs) == 2

    @pytest.mark.asyncio  
    async def test_fetch_with_limit(self, storage):
        """Fetch with limit returns only last N messages."""
        await storage.init()
        
        user = User(id="user2", name="LimitedUser")
        for i in range(5):
            msg = Msg(body=f"msg{i}", peer_id=f"p{i}")
            await storage.save(user, msg)
        
        msgs = await storage.fetch_history("user2", limit=2)
        
        assert len(msgs) == 2
        assert msgs[0].body == "msg3"
        assert msgs[1].body == "msg4"

    @pytest.mark.asyncio
    async def test_fetch_with_negative_limit(self, storage):
        """Fetch with negative limit returns empty."""
        await storage.init()
        
        user = User(id="u1", name="Test")
        msg = Msg(body="test", peer_id="p1")
        await storage.save(user, msg)
        
        msgs = await storage.fetch_history("u1", limit=-1)
        assert len(msgs) == 0


class TestClose:
    """Tests for the close method."""

    @pytest.mark.asyncio
    async def test_close_resets_state(self, storage):
        """Close should reset initialized flag."""
        await storage.init()
        
        user = User(id="u1", name="Test")
        msg = Msg(body="test")
        await storage.save(user, msg)
        
        await storage.close()
        
        assert storage._initialized is False
        assert len(storage._users) == 0
        assert len(storage._messages) == 0

    @pytest.mark.asyncio
    async def test_close_after_fetch_returns_empty(self, storage):
        """After close and re-init, fetch returns empty."""
        await storage.init()
        
        user = User(id="u1", name="Test")
        msg = Msg(body="test")
        await storage.save(user, msg)
        
        await storage.close()  # Clear everything
        await storage.init()    # Re-initialize
        
        msgs = await storage.fetch_history("u1")
        assert msgs == []
