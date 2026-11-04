from typing import AsyncGenerator, Optional

try:
    from typing import Protocol, runtime_checkable  # Python 3.8+
except ImportError:
    from typing_extensions import Protocol, runtime_checkable


class Transport(Protocol):
    async def send(self, message: str) -> bool: ...

    async def stream(self) -> AsyncGenerator[str, None]: ...

    async def close(self) -> None: ...


@runtime_checkable
class Storage(Protocol):
    async def init(self) -> None: ...

    async def save(self, user: str, msg: str, timestamp: int | None = None) -> bool: ...

    async def fetch_history(self, limit: int) -> list[tuple[str, str, int]]: ...

    async def close(self) -> None: ...
