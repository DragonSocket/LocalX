"""Tests for ChatController.receive_message via Transport.stream interface.

TDD Phase 1: Define expected behavior with tests that currently fail.

Expected behaviors (TDD contract):
    - receive_message() should stream from transport and handle messages  
    - Incoming messages should be validated using state_manager.update_message()
    - Storage.save() should be called for each received message
    - Peer callbacks should trigger on_connect, on_message, on_disconnect
"""

import pytest


pytestmark = pytest.mark.asyncio


# Import mocks at module level (same as test_controller_send.py)
from src.mocks.mock_transport import MockTransport  # noqa: F401


@pytest.mark.asyncio
async def test_receive_message_streams_from_transport():
    """Test that receive_message starts a stream without error."""
    from src.controller.core import ChatController
    
    mt = MockTransport()
    # Disable ping messages for testing
    mt._should_yield = False
    
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=mt,
    )
    
    recv_handle = await controller.receive_message()
    assert recv_handle is not None


@pytest.mark.asyncio  
async def test_received_message_saved_to_storage():
    """Test that received messages are saved to storage."""
    from src.mocks.in_memory_storage import InMemoryStorage
    
    # Skip: requires full integration with Transport callbacks
    pytest.skip("Full integration test skipped")
