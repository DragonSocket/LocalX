"""Tests for NcatTransport implementation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


class TestNcatTransport:
    """Test suite verifying NcatTransport Protocol compliance."""

    def test_init_takes_host_port(self):
        """Verify constructor signature."""
        from src.transport.ncat import NcatTransport
        
        t = NcatTransport("127.0.0.1", 5000)
        assert t._host == "127.0.0.1"

    @pytest.mark.asyncio  
    async def test_connect_sends_command(self):
        """Test connect() calls subprocess correctly."""
        from src.transport.ncat import NcatTransport
        
        with patch("src.transport.ncat.asyncio.create_subprocess_exec") as mock_spawn:
            t = NcatTransport("test.com", 80)
            
            # Connect should spawn subprocess
            try:
                await t.connect()
            except Exception:
                pass
            
            assert mock_spawn.called

    @pytest.mark.asyncio
    async def test_send_requires_connection(self):
        """Ensure send returns False when disconnected."""
        from src.transport.ncat import NcatTransport
        
        t = NcatTransport("x", 1)
        result = await t.send("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_stream_returns_coroutine(self):
        """Stream returns coroutine matching AsyncGenerator protocol."""
        from src.transport.ncat import NcatTransport
        
        t = NcatTransport("x", 1)
        coro = t.stream()
        assert asyncio.iscoroutine(coro)

    @pytest.mark.asyncio
    async def test_close_no_crash(self):
        """Close doesn't crash even when not connected."""
        from src.transport.ncat import NcatTransport
        
        t = NcatTransport("localhost", 80)
        await t.close()

    @pytest.mark.asyncio
    async def test_aenter_aexit_exist(self):
        """Async context manager methods exist."""
        assert hasattr(NcatTransport, "__aenter__")
        assert hasattr(NcatTransport, "__aexit__")

    async def test_inherits_transport_protocol(self):
        """NcatTransport satisfies Transport Protocol."""
        from src.transport.ncat import NcatTransport
        from src.interfaces import Transport
        
        t = NcatTransport("x", 1)
        
        assert hasattr(t, "send")
        assert hasattr(t, "stream")  
        assert hasattr(t, "close")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
