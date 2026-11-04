"""Tests for protocol interfaces.

These tests verify that:
1. Our implementations adhere to the protocols
2. The runtime_checkable decorators work correctly
3. Protocol validation works with duck typing
"""

import pytest
import sys
sys.path.insert(0, '/home/blastmerder/Documents/projects/python/localX/src')

from interfaces import Transport, Storage


# =============================================================================
# Transport Tests
# =============================================================================
class MockTransportImpl:
    """Simple implementation to test protocol conformance."""
    
    async def send(self, message):
        return  # In reality would raise or save
    
    async def stream(self):
        yield "test message"
        return
    
    async def close(self):
        pass


def test_transport_protocol_check():
    """Verify that our implementation matches the Transport protocol."""
    mock_impl = MockTransportImpl()
    
    # Runtime check
    assert isinstance(mock_impl, Transport), "MockTransportImpl should conform to Transport protocol"
    
    # Check methods exist with correct signatures
    import asyncio
    
    async def _check():
        # Verify send accepts str and returns None (async)
        await mock_impl.send("test")
        
        # Verify stream is async generator
        gen = mock_impl.stream()
        assert hasattr(gen, '__anext__'), "stream must be an async generator"
        result = await gen.__anext__() if hasattr(gen, '__anext__') else None
        assert result is None or result == "test message"
        
        # Verify close works
        await mock_impl.close()
    
    asyncio.run(_check())


# =============================================================================
# Storage Tests
# =============================================================================
class MockStorageImpl:
    """Simple implementation to test protocol conformance."""
    
    async def init(self):
        pass
    
    async def save(self, user, msg):
        pass
    
    async def fetch_history(self, limit=50):
        return []
    
    async def close(self):
        pass


def test_storage_protocol_check():
    """Verify that our implementation matches the Storage protocol."""
    mock_impl = MockStorageImpl()
    
    # Runtime check
    assert isinstance(mock_impl, Storage), "MockStorageImpl should conform to Storage protocol"
    
    # Check methods exist
    asyncio.run(mock_impl.init())
    asyncio.run(mock_impl.save("alice", "hello"))
    result = asyncio.run(mock_impl.fetch_history(10))
    assert isinstance(result, list)
    asyncio.run(mock_impl.close())


if __name__ == "__main__":
    test_transport_protocol_check()
    test_storage_protocol_check()
    print("All interface conformance tests passed!")
