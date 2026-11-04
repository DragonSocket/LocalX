"""Tests for ChatController.send_message via Transport interface.

TDD Phase 1: Define expected behavior with tests that currently fail.
"""

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_send_message_through_transport():
    """send_message should call transport.send() with the raw message."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    
    from controller import ChatController
    from mocks.mock_transport import MockTransport
    
    mt = MockTransport()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=mt,
    )
    
    msg = "Hello, peer!"
    await controller.send_message(msg)
    
    # Verify transport was called correctly
    assert len(mt.sent_messages) == 1
    assert mt.sent_messages[0] == msg


@pytest.mark.asyncio
async def test_send_message_to_specific_peer():
    """send_message can target a specific peer."""
    from mocks.mock_transport import MockTransport
    from controller import ChatController
    
    mt = MockTransport()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=mt,
    )
    
    peer_name = "Alice"
    msg = f"Hai {peer_name}!"
    
    await controller.send_message(msg, peer=peer_name)
    
    # Transport should store the peer info
    assert len(mt.sent_messages) == 1


@pytest.mark.asyncio
async def test_send_message_with_empty_string():
    """send_message with empty string should return False and report error via state_manager."""
    from mocks.mock_transport import MockTransport
    from controller import ChatController
    
    mt = MockTransport()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=mt,
    )
    
    result = await controller.send_message("")
    assert result is False
    # Check error was recorded in system state
    assert controller.state_manager.system.last_error and "empty" in controller.state_manager.system.last_error.lower() or "invalid" in controller.state_manager.system.last_error.lower()


@pytest.mark.asyncio
async def test_send_message_too_long():
    """send_message with message > 100 chars should return False and report error via state_manager."""
    from mocks.mock_transport import MockTransport
    from controller import ChatController
    
    mt = MockTransport()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=mt,
    )
    
    long_msg = "x" * 101
    
    result = await controller.send_message(long_msg)
    assert result is False
    # Check error was recorded in system state
    assert controller.state_manager.system.last_error and ("too long" in controller.state_manager.system.last_error.lower() or "long" in controller.state_manager.system.last_error.lower())


@pytest.mark.asyncio
async def test_send_message_with_html_injection():
    """send_message should forward raw message through Transport safely."""
    from mocks.mock_transport import MockTransport
    from controller import ChatController
    
    mt = MockTransport()
    controller = ChatController(
        name="TestUser",
        host="localhost",
        port=12345,
        storage=None,
        transport=mt,
    )
        
    # XSS test - Transport handles the formatting
    msg = "<script>evil()</script>"
    await controller.send_message(msg)



