import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import time


@dataclass
class Msg:
    body: str
    peer_id: str | None = None
    timestamp: float = field(default_factory=time.time)

@dataclass  
class User:
    id: str
    name: str


class InMemoryStorage:
    """Mock storage implementation for testing."""

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._messages: Dict[str, List[Msg]] = {}
        self._initialized = False

    async def init(self) -> None:
        """Initialize storage (mock - always succeeds)."""
        self._initialized = True

    async def save(self, user: User, msg: Msg) -> bool:
        """Save a message for a user."""
        if not self._initialized:
            raise RuntimeError("Storage not initialized")
        
        # Auto-register user
        if user.id not in self._users:
            self._users[user.id] = user
        
        if user.id not in self._messages:
            self._messages[user.id] = []
        self._messages[user.id].append(msg)

        return True

    async def fetch_history(self, user_id: str, limit: int | None = None) -> List[Msg]:
        """Fetch message history for a user."""
        if not self._initialized or user_id not in self._users:
            return []
        
        messages = self._messages.get(user_id, [])
        
        # Sort by timestamp ascending (oldest first)
        sorted_msgs = sorted(messages, key=lambda m: m.timestamp)
        
        if limit is None:
            return sorted_msgs
        if limit <= 0:
            return []
        # Return last N messages (most recent), sorted chronologically
        return sorted_msgs[-limit:]

    async def close(self) -> None:
        """Close storage (mock - no-op)."""
        self._users.clear()
        self._messages.clear()
        self._initialized = False
