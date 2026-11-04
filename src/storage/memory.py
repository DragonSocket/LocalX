from __future__ import annotations

import time


class InMemoryStorage:
    """In-memory implementation of Storage protocol for testing."""

    def __init__(self) -> None:
        self._messages: list[tuple[str, str, int]] = []

    async def init(self) -> None:
        pass

    async def save(self, user: str, msg: str, timestamp: int | None = None) -> bool:
        ts = timestamp or int(time.time() * 1000)
        self._messages.append((user, msg, ts))
        return True

    async def fetch_history(self, limit: int) -> list[tuple[str, str, int]]:
        limit = limit or len(self._messages)
        result = self._messages[-limit:] if limit > 0 else []
        # Sort by timestamp ascending (oldest first)
        return sorted(result, key=lambda m: m[2])

    async def close(self) -> None:
        pass
