"""SQLite implementation of Storage protocol using aiosqlite."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import aiosqlite

from src.interfaces import Storage


class SqliteStorage(Storage):
    """Async SQLite storage implementation using aiosqlite."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize with database path.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path).resolve()
        self._closed = False
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        """Initialize the database and create tables if not exists."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    user TEXT NOT NULL,
                    msg TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    PRIMARY KEY (user, timestamp)
                )
            """)
            await db.commit()

    async def save(
        self, user: str, msg: str, timestamp: int | None = None
    ) -> bool:
        """Save a message to the database.
        
        Args:
            user: Username who sent the message.
            msg: Message content.
            timestamp: Optional Unix timestamp in milliseconds. If None, uses current time.
            
        Returns:
            True if save was successful.
            
        Raises:
            RuntimeError: If storage is closed.
        """
        if self._closed:
            raise RuntimeError("Storage is closed")
        
        ts = timestamp or int(time.time() * 1000)
        
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            # Use INSERT OR REPLACE to handle potential duplicates gracefully
            await db.execute(
                "INSERT OR REPLACE INTO messages (user, msg, timestamp) VALUES (?, ?, ?)",
                (user, msg, ts),
            )
            await db.commit()
        
        return True

    async def fetch_history(self, limit: int) -> list[tuple[str, str, int]]:
        """Fetch most recent messages.
        
        Args:
            limit: Number of messages to fetch (0+ means all).
            
        Returns:
            List of tuples (user, msg, timestamp), oldest first.
            
        Raises:
            RuntimeError: If storage is closed.
        """
        if self._closed:
            raise RuntimeError("Storage is closed")
        
        if limit == 0:
            limit = 1_000_000  # Fetch all reasonably
        
        async with self._lock, aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user, msg, timestamp FROM messages ORDER BY timestamp ASC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
        
        return [(row[0], row[1], row[2]) for row in rows]

    async def close(self) -> None:
        """Close the storage connection."""
        self._closed = True
