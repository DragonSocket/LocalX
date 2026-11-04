"""Storage Implementation Module.

This module provides implementations of the Storage protocol:
- InMemoryStorage (for development/testing)
- SqliteStorage (for production - will be implemented next)

Usage via Dependency Injection:
    storage = ServiceLocator.get_dependency(Storage)  # Resolves implementation
"""

from typing import AsyncGenerator, Protocol, runtime_checkable
from dataclasses import dataclass
import asyncio
import time

from interfaces import Storage as StorageBase


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
    
    Uses a deque for efficient O(1) append/pop operations.
    Perfect for TDD before replacing with persistent SQLite storage.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize the in-memory storage.
        
        Args:
            max_history: Maximum messages to keep in memory (default: 1000).
        """
        self._messages: list[Message] = []
        self.max_history = max_history
    
    async def init(self) -> None:
        """Initialize storage - nothing to do in memory."""
        pass
    
    async def save(self, username: str, message: str) -> None:
        """
        Save a message from a user.
        
        Args:
            username: The sender's username.
            message: The message text to store.
        """
        msg = Message(
            id=len(self._messages) + 1,
            sender=username,
            message=message,
            timestamp=time.monotonic()
        )
        self._messages.append(msg)
        
        # Maintain max_history limit - remove oldest AND keep only last N
        if len(self._messages) > self.max_history:
            # Remove excess by slicing to keep only the last max_history items
            excess = len(self._messages) - self.max_history
            self._messages = self._messages[excess:]
            
    async def fetch_history(self, limit: int = 50) -> list[dict]:
        """
        Fetch the most recent messages.
        
        Args:
            limit: Maximum number of messages to return (default: 50).
            
        Returns:
            List of message dictionaries, newest first.
        """
        # Take top 'limit' from the end and reverse to get newest first
        remaining = len(self._messages)
        recent_count = min(limit, remaining)
        recent = self._messages[-recent_count:]
        return [msg.to_dict() for msg in reversed(recent)]
    
    async def close(self) -> None:
        """Close storage - nothing to cleanup."""
        pass


class StorageError(Exception):
    """Base class for storage-related errors."""
    pass
