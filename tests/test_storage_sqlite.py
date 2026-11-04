"""Tests for SqliteStorage implementation."""

import asyncio
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import aiosqlite

from interfaces import Storage
from storage.sqlite import SqliteStorage


@pytest.fixture
async def temp_db(tmp_path: Path) -> str:
    """Create a temporary database file."""
    db_path = tmp_path / "test.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


class TestSqliteStorage:
    """Tests for SqliteStorage class."""

    @pytest.mark.asyncio
    async def test_init_creates_database(
        self, temp_db: str
    ) -> None:
        """Test that init creates the database and messages table."""
        storage = SqliteStorage(str(temp_db))
        await storage.init()
        
        async with aiosqlite.connect(temp_db) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
            )
            row = await cursor.fetchone()
            assert row is not None, "Messages table should be created"

    @pytest.mark.asyncio
    async def test_save_message(self, temp_db: str) -> None:
        """Test saving a single message."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        result = await storage.save("user1", "Hello world!")
        
        assert result is True
        async with aiosqlite.connect(temp_db) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE user='user1' AND msg='Hello world!'"
            )
            count = await cursor.fetchone()
            assert count[0] == 1

    @pytest.mark.asyncio
    async def test_save_message_with_timestamp(self, temp_db: str) -> None:
        """Test saving a message with explicit timestamp."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        # Use a timestamp in the future (in milliseconds)
        base_ts = 1_700_000_000_000
        ts = base_ts + 123
        
        result = await storage.save("user1", "Timestamped msg", timestamp=ts)
        
        assert result is True
        async with aiosqlite.connect(temp_db) as db:
            cursor = await db.execute(
                "SELECT user, msg, timestamp FROM messages WHERE user='user1' AND msg='Timestamped msg'"
            )
            row = await cursor.fetchone()
            # Timestamp should match exactly (row[2] is timestamp column)
            assert row[2] == ts

    @pytest.mark.asyncio
    async def test_save_multiple_messages(self, temp_db: str) -> None:
        """Test saving multiple messages."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        await storage.save("alice", "msg1")
        await storage.save("bob", "msg2")
        await storage.save("alice", "msg3")
        
        async with aiosqlite.connect(temp_db) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            count = await cursor.fetchone()
            assert count[0] == 3

    @pytest.mark.asyncio
    async def test_fetch_history_positive_limit(
        self, temp_db: str
    ) -> None:
        """Test fetching history with a positive limit."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        # Add messages with small delays to ensure different timestamps
        await storage.save("u1", "m1")
        await asyncio.sleep(0.0001)
        await storage.save("u2", "m2")
        await asyncio.sleep(0.0001)
        await storage.save("u3", "m3")
        
        history = await storage.fetch_history(2)
        
        assert len(history) == 2
        
        # Verify ordered oldest first (not newest first)
        assert history[0][2] < history[1][2]

    @pytest.mark.asyncio
    async def test_fetch_history_full(
        self, temp_db: str
    ) -> None:
        """Test fetching all messages with limit=0 or large limit."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        for i in range(5):
            await storage.save(f"user{i}", f"msg_{i}")
        
        history = await storage.fetch_history(0)  # Fetch all
        
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_fetch_history_empty(self, temp_db: str) -> None:
        """Test fetching history when no messages exist."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        history = await storage.fetch_history(10)
        
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_fetch_oldest_first(
        self, temp_db: str
    ) -> None:
        """Test that messages are returned oldest first."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        # Save in different order, but time.sleep ensures timestamp ordering
        timestamp = int(time.time() * 1000) - 1000
        await storage.save("u", "newer")
        await asyncio.sleep(0.01)
        timestamp2 = int(time.time() * 1000) - 500
        await storage.save("u", "older", timestamp=timestamp2)
        await asyncio.sleep(0.01)
        timestamp3 = int(time.time() * 1000)
        await storage.save("u", "newest", timestamp=timestamp3)
        
        history = await storage.fetch_history(3)
        
        assert len(history) == 3
        
        # Timestamps should be in ascending order (oldest first)
        for i in range(len(history) - 1):
            assert history[i][2] <= history[i + 1][2]

    @pytest.mark.asyncio
    async def test_close_closes_db(
        self, temp_db: str
    ) -> None:
        """Test that close properly marks storage as closed."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        await storage.save("u", "m")
        
        # Check _closed state after close
        await storage.close()
        assert storage._closed

    @pytest.mark.asyncio
    async def test_double_init_safe(
        self, temp_db: str
    ) -> None:
        """Test that calling init twice doesn't crash."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        # Should not raise
        await storage.init()

    @pytest.mark.asyncio
    async def test_save_after_close_raises(
        self, temp_db: str
    ) -> None:
        """Test that saving after close raises an error."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        await storage.close()
        
        with pytest.raises(RuntimeError):
            await storage.save("u", "m")

    @pytest.mark.asyncio
    async def test_fetch_history_after_close_raises(
        self, temp_db: str
    ) -> None:
        """Test that fetching history after close raises an error."""
        storage = SqliteStorage(temp_db)
        await storage.init()
        
        await storage.save("u", "m")
        await storage.close()
        
        with pytest.raises(RuntimeError):
            await storage.fetch_history(1)
