import asyncio
from typing import AsyncGenerator, Dict, Optional
from dataclasses import dataclass


@dataclass
class TransportStatus:
    connected: bool


class MockTransport:
    """Mock transport for testing - simulates network without ncat."""

    def __init__(self):
        self._status = TransportStatus(connected=False)
        self._callbacks: Dict[str, list] = {
            "peer_connected": [],
            "message_received": [],
            "disconnected": []
        }
        
        # Use a lock and simple iteration for stream
        self._stream_iter_iter = 0
        self._should_yield = True

    async def stream(self) -> AsyncGenerator[str, None]:
        """Mock stream - yields ping messages while connected."""
        while self._status.connected:
            yield f"PONG_{self._stream_iter_iter}"
            self._stream_iter_iter += 1
            await asyncio.sleep(0.1)  # Simulate network activity

    async def connect(self, host: str, port: int) -> None:
        """Mock connection - always succeeds."""
        import uuid
        self._status.connected = True
        self.id = f"{uuid.uuid4().hex[:8]}@{host}:{port}"
        
        # Simulate peer connected event
        loop = asyncio.get_event_loop()
        for callback in self._callbacks["peer_connected"]:
            await callback(self)

    async def send(self, message: str) -> bool:
        """Mock send - always succeeds."""
        # Store sent messages for testing transport.send() interface
        if not hasattr(self, '_sent_messages'):
            self._sent_messages = []
        
        self._sent_messages.append(message)
        
        loop = asyncio.get_event_loop()
        for callback in self._callbacks["message_received"]:
            await callback(self, message)
        return True

    async def close(self) -> None:
        """Close connection."""
        self._status.connected = False
        self.id = None
        # Reset iterator to prevent hanging generators
        self._stream_iter_iter = 0
    
    def on_connect(self, cb):
        self._callbacks["peer_connected"].append(cb)
    
    def on_message(self, cb):
        self._callbacks["message_received"].append(cb)
    
    def on_disconnect(self, cb):
        self._callbacks["disconnected"].append(cb)

    @property
    def sent_messages(self) -> list[str]:
        """Property exposing sent messages list."""
        return getattr(self, '_sent_messages', [])