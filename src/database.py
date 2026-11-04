"""Storage Implementation Module.

This module provides implementations of the Storage protocol:
- InMemoryStorage (for development/testing)
- SqliteStorage (for production)

Usage via Dependency Injection:
    storage = ServiceLocator.get_dependency(Storage)  # Resolves implementation
"""

import asyncio
import time
import aiosqlite
from typing import AsyncGenerator, Protocol, runtime_checkable
from dataclasses import dataclass

from src.interfaces import Storage as StorageBase


@dataclass
class Message:
    """Stored message with metadata."""
    
    id: int
    sender: str
    message: str
    timestamp: float
    
    def to_dict(self) -> dict:
        return self.__dict__


class InMemoryStorage(StorageBase):
    """
    In-memory storage implementation for development and testing.
    """
    
    def __init__(self, max_history: int = 1000):
        self._messages: list[Message] = []
        self.max_history = max_history
    
    async def init(self) -> None:
        pass
    
    async def save(self, username: str, message: str, timestamp: int | None = None) -> bool:
        msg = Message(
            id=len(self._messages) + 1,
            sender=username,
            message=message,
            timestamp=float(timestamp) if timestamp else time.time()
        )
        self._messages.append(msg)
        
        if len(self._messages) > self.max_history:
            excess = len(self._messages) - self.max_history
            self._messages = self._messages[excess:]
        return True
    
    async def fetch_history(self, limit: int = 50) -> list[tuple[str, str, int]]:
        remaining = len(self._messages)
        recent_count = min(limit, remaining)
        recent = self._messages[-recent_count:]
        return [(msg.sender, msg.message, int(msg.timestamp)) for msg in reversed(recent)]
    
    async def close(self) -> None:
        pass


class SqliteStorage(StorageBase):
    """
    Persistent SQLite storage implementation.
    """

    def __init__(self, db_path: str = "chat.db"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Initialize database and create tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
        """)
        await self._conn.commit()

    async def save(self, username: str, message: str, timestamp: int | None = None) -> bool:
        """Save a message to SQLite."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")
        
        ts = timestamp if timestamp is not None else int(time.time())
        try:
            await self._conn.execute(
                "INSERT INTO messages (sender, message, timestamp) VALUES (?, ?, ?)",
                (username, message, ts)
            )
            await self._conn.commit()
            return True
        except Exception:
            return False

    async def fetch_history(self, limit: int = 50) -> list[tuple[str, str, int]]:
        """Fetch history from SQLite."""
        if not self._conn:
            raise RuntimeError("Storage not initialized. Call init() first.")
            
        try:
            async with self._conn.execute(
                "SELECT sender, message, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                # SQLite returns tuples: (sender, message, timestamp)
                return [(row[0], row[1], row[2]) for row in rows]
        except Exception:
            return []

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None


class StorageError(Exception):
    """Base class for storage-related errors."""
    pass
