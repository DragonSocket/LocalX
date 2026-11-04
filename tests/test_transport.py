import pytest
import asyncio
from src.mocks.mock_transport import MockTransport, TransportStatus


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def transport():
    """Create a fresh MockTransport instance."""
    return MockTransport()


class TestConnect:
    """Tests for the connect method."""

    @pytest.mark.asyncio
    async def test_connect_succeeds(self, transport):
        """Connect should always succeed and set connected flag."""
        await transport.connect("127.0.0.1", 8080)
        
        assert transport._status.connected is True
        assert transport.id is not None

    @pytest.mark.asyncio
    async def test_connect_sets_id(self, transport):
        """Connect should set the peer id."""
        await transport.connect("example.com", 9000)
        
        assert transport.id
        assert ":" in transport.id
        assert "example.com" in transport.id


class TestSend:
    """Tests for the send method."""

    @pytest.mark.asyncio
    async def test_send_succeeds(self, transport, event_loop):
        """Send should return True on success."""
        await transport.connect("127.0.0.1", 8080)
        
        result = await transport.send("Hello, World!")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_send_with_empty_string(self, transport):
        """Send with empty string should succeed."""
        await transport.connect("127.0.0.1", 8080)
        
        result = await transport.send("")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_send_with_special_chars(self, transport):
        """Send with special characters should succeed."""
        await transport.connect("127.0.0.1", 8080)
        
        msg = "Line1\nLine2\tTab\rCR & $Special"
        result = await transport.send(msg)
        
        assert result is True


class TestStream:
    """Tests for the stream method."""

    @pytest.mark.asyncio
    async def test_stream_returns_generator(self, transport):
        """Stream should return an async generator."""
        await transport.connect("127.0.0.1", 8080)
        
        result = transport.stream()
        
        # AsyncGenerator is awaitable in Python 3.12+ but not a coroutine
        from types import AsyncGeneratorType
        assert isinstance(result, AsyncGeneratorType)

    @pytest.mark.asyncio
    async def test_stream_yields_on_connected(self, transport):
        """Stream should yield values while connected."""
        await transport.connect("127.0.0.1", 8080)
        
        gen = transport.stream()
        
        # Should be able to iterate at least once when connected
        count = 0
        async for msg in gen:
            count += 1
            if count >= 3:
                break
        
        assert count > 0

    @pytest.mark.asyncio
    async def test_stream_stops_on_close(self, transport):
        """Stream should stop when connection is closed."""
        await transport.connect("127.0.0.1", 8080)
        
        # Collect some messages
        msgs = []
        async for msg in transport.stream():
            msgs.append(msg)
            if len(msgs) >= 3:
                break
        
        # Close connection
        await transport.close()
        
        # Attempt to get another message after close should raise StopAsyncIteration or timeout
        gen = transport.stream()
        try:
            msg = await asyncio.wait_for(gen.__anext__(), timeout=0.5)
            assert False, "Should not receive messages after close"
        except (StopAsyncIteration, TimeoutError):
            pass  # Expected
        
        assert transport._status.connected is False


class TestClose:
    """Tests for the close method."""

    @pytest.mark.asyncio
    async def test_close_disconnects(self, transport):
        """Close should disconnect and reset connected flag."""
        await transport.connect("127.0.0.1", 8080)
        
        await transport.close()
        
        assert transport._status.connected is False
        # ID may remain after close (connection info might be cached)

    @pytest.mark.asyncio
    async def test_close_multiple_times_idempotent(self, transport):
        """Close can be called multiple times."""
        await transport.connect("127.0.0.1", 8080)
        
        await transport.close()
        await transport.close()
        
        assert transport._status.connected is False

    @pytest.mark.asyncio
    async def test_close_without_connect(self, transport):
        """Close without connect should not raise."""
        # Don't call connect
        
        await transport.close()
        
        assert transport._status.connected is False


class TestCallbackEvents:
    """Tests for event callbacks."""

    @pytest.mark.asyncio
    async def test_on_connect_called(self, transport):
        """Connect callback should be called when connecting."""
        connected = []
        
        async def on_connect(tc):
            connected.append(True)
        
        transport.on_connect(on_connect)
        
        await transport.connect("127.0.0.1", 8080)
        
        assert len(connected) >= 1

    @pytest.mark.asyncio
    async def test_on_message_called(self, transport):
        """Message callback should be called on send."""
        messages = []
        
        async def on_msg(tc, msg):
            messages.append(msg)
        
        transport.on_message(on_msg)
        await transport.connect("127.0.0.1", 8080)
        
        await transport.send("test message")
        
        assert "test message" in messages

