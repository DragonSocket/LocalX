from typing import Protocol, AsyncGenerator, runtime_checkable

@runtime_checkable
class Transport(Protocol):
    async def send(self, message: str) -> None:
        ...

    async def stream(self) -> AsyncGenerator[str, None]:
        ...

    async def close(self) -> None:
        ...

@runtime_checkable
class Storage(Protocol):
    async def init(self) -> None:
        ...

    async def add_message(self, username: str, message: str) -> None:
        ...

    async def get_history(self, limit: int = 50) -> list[dict]:
        ...

    async def close(self) -> None:
        ...

