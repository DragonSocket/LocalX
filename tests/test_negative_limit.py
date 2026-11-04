import pytest
import asyncio
from src.mocks.in_memory_storage import InMemoryStorage, Msg, User


@pytest.fixture
def storage():
    """Create a fresh InMemoryStorage instance."""
    return InMemoryStorage()


@pytest.mark.asyncio
async def test_fetch_with_negative_limit(storage):
    """Fetch with limit=-1 returns all messages (empty history)."""
    await storage.init()
    
    user = User(id="user3", name="NegativeUser")
    msg = Msg(body="test", peer_id="p1")
    await storage.save(user, msg)
    
    msgs = await storage.fetch_history("user3", limit=-1)
    assert len(msgs) == 0
