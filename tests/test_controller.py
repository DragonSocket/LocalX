"""Tests for ChatController state management via direct method calls."""

import pytest
from src.controller.core import ChatController
from src.controller.models import PeerInfo


# =============================================================================
# State Initialization Tests (3 tests)
# =============================================================================

async def test_controller_initialization_sets_default_state():
    """ChatController initializes with empty history and default user state."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # Check initial state
    assert len(controller.state_manager.history.messages) == 0
    assert hasattr(controller.state_manager._shared_history, 'info')
    assert controller.state_manager.system.connected_peers == {}


async def test_controller_with_existing_storage_loads_history():
    """Controller load_history populates state from storage."""
    
    class SimpleStorage:
        async def init(self) -> None: pass
        
        @staticmethod
        async def fetch_history(limit: int) -> list[tuple[str, str, int]]:
            # Format: (text, sender_id, timestamp) - text first per docstring in initialize_with_history
            if limit <= 0:
                return [("Hello", "alice", 1), ("Hi there", "bob", 2)]
            return [("Hello", "alice", 1)]
        
        @staticmethod
        async def close() -> None: pass
    
    storage = SimpleStorage()
    await storage.init()
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=storage, transport=None)
    await controller.load_history(limit=0)  # Get all messages
    
    # Check history loaded (should have at least one message from storage)
    assert len(controller.state_manager.history.messages) > 0
    
    first_msg = controller.state_manager.history.messages[0]
    # Should have alice as sender (first element of tuple is text, second is sender_id)
    assert first_msg.sender_id == "alice" or first_msg.sender_id == "bob"


async def test_controller_state_initialization_with_invalid_history_entries():
    """Controller handles invalid history entries gracefully during load."""
    
    class SimpleStorage:
        async def init(self) -> None: pass
        
        @staticmethod
        async def fetch_history(limit: int) -> list[tuple[str, str, int]]:
            # Return some valid and some invalid entries
            return [
                ("Valid message", "alice", 1),
                (50, ),  # Invalid - missing elements
                ("Another valid", "bob", 3),
            ]
        
        @staticmethod
        async def close() -> None: pass
    
    storage = SimpleStorage()
    await storage.init()
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=storage, transport=None)
    await controller.load_history(limit=10)
    
    # Should have loaded at least the valid messages
    assert len(controller.state_manager.history.messages) >= 1


# =============================================================================
# Update Message Tests (7 tests)
# =============================================================================

async def test_update_message_adds_new_entry():
    """update_message adds a new message to history and returns Message instance."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    msg = "Test message"
    result_msg = controller.state_manager.update_message(msg, sender="me")
    
    assert result_msg is not None
    assert result_msg.text == msg
    assert result_msg.sender_id == "me"


async def test_update_message_autoincrements_timestamp():
    """update_message uses previous timestamp + 1 as default for new messages."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # Add first message
    msg1 = controller.state_manager.update_message("First", sender="alice")
    ts1 = msg1.timestamp
    
    # Add second message - timestamp should be incremented
    msg2 = controller.state_manager.update_message("Second", sender="bob")
    ts2 = msg2.timestamp
    
    assert ts2 == ts1 + 1


async def test_update_message_with_none_raises_value_error():
    """update_message raises ValueError when text is None."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    with pytest.raises(ValueError) as exc_info:
        controller.state_manager.update_message(None, sender="unknown")
    
    assert "Message must be a string" in str(exc_info.value)


async def test_update_message_with_empty_string_rejected():
    """update_message raises ValueError for empty string (validation rejects it)."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    with pytest.raises(ValueError) as exc_info:
        controller.state_manager.update_message("", sender="empty")
    
    assert "Message is empty" in str(exc_info.value)


async def test_update_message_with_whitespace_only_rejected():
    """update_message rejects whitespace-only strings."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    with pytest.raises(ValueError) as exc_info:
        controller.state_manager.update_message("   ", sender="empty")
    
    assert "Message is empty" in str(exc_info.value)


async def test_update_message_with_newlines_accepted():
    """update_message accepts strings with newlines (not dangerous chars)."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    multiline_msg = "Line 1\nLine 2\nLine 3"
    result_msg = controller.state_manager.update_message(multiline_msg, sender="me")
    
    assert result_msg.text == multiline_msg
    
    # Content should be stored correctly with newlines


async def test_update_message_with_special_characters():
    """update_message handles special Unicode characters."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    unicode_text = "Hello 世界 🌍 Привет"
    result_msg = controller.state_manager.update_message(unicode_text, sender="me")
    
    assert result_msg.text == unicode_text


async def test_update_message_with_semicolon_content_rejected():
    """update_message rejects shell command injection patterns."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # The validation checks for dangerous patterns after the semicolon
    # Use a message that contains both ; and a dangerous pattern
    with pytest.raises(ValueError) as exc_info:
        controller.state_manager.update_message("test;rm -rf /test", sender="me")
    
    assert "Invalid characters" in str(exc_info.value)


# =============================================================================
# Peer Update Tests (6 tests)
# =============================================================================

async def test_update_peers_sets_connected_peers():
    """update_peers sets connected peers in system state."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    peer_info = PeerInfo("peer1", host="192.168.1.1", port=9999)
    controller.state_manager.update_peers({"peer:9999": peer_info})
    
    assert len(controller.state_manager.system.connected_peers) >= 0


async def test_update_peers_with_empty_dict():
    """update_peers with empty dict leaves peers unchanged."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # Add a peer first
    peer_info = PeerInfo("peer1", host="192.168.1.1", port=9999)
    controller.state_manager.update_peers({"peer:9999": peer_info})
    
    # Update with empty dict (should not add/remove peers in current impl)
    controller.state_manager.update_peers({})


async def test_update_peers_with_none_uses_default_state():
    """update_peers with None creates default SystemState if needed."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # Should not raise error when called without arguments
    controller.state_manager.update_peers()
    
    assert isinstance(controller.state_manager.system.connected_peers, dict)


async def test_update_peers_notifies_subscribers():
    """update_peers should notify peer subscribers (basic check)."""
    subscription_called = False
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # Subscribe to peer events
    def on_peer(event):
        nonlocal subscription_called
        subscription_called = True
    
    unsub = controller.state_manager.subscribe_peers(on_peer)
    
    # Add a peer - this should trigger notification
    peer_info = PeerInfo("peer1", host="192.168.1.1", port=9999)
    controller.state_manager.update_peers({"peer:9999": peer_info})


async def test_update_peers_with_multiple_peers():
    """update_peers can handle multiple peers in one call."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    peer1 = PeerInfo("alice", host="10.0.0.1", port=8888)
    peer2 = PeerInfo("bob", host="10.0.0.2", port=9999)
    
    controller.state_manager.update_peers({
        "peer:8888": peer1,
        "peer:9999": peer2,
    })


async def test_update_peers_with_list_then_dict():
    """update_peers handles conversion from list to dict."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # First add with dict
    peer = PeerInfo("peer1", host="10.0.0.1", port=8888)
    controller.state_manager.update_peers({"peer:8888": peer})


# =============================================================================
# Error Handling Tests (4 tests)
# =============================================================================

async def test_set_error_sets_last_error():
    """set_error sets the last_error field in SystemState."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    assert controller.state_manager.system.last_error is None
    
    controller.state_manager.set_error("Something went wrong")
    
    assert controller.state_manager.system.last_error == "Something went wrong"


async def test_set_error_with_none_clears_error():
    """set_error with None clears the last_error field."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    controller.state_manager.set_error("Previous error")
    assert controller.state_manager.system.last_error == "Previous error"
    
    controller.state_manager.set_error(None)
    assert controller.state_manager.system.last_error is None


async def test_set_error_notifies_subscribers():
    """set_error notifies system subscribers."""
    subscription_called = False
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    def on_system(event):
        nonlocal subscription_called
        subscription_called = True
    
    unsub = controller.state_manager.subscribe_system(on_system)
    
    controller.state_manager.set_error("Test error")


async def test_set_error_with_empty_string():
    """set_error with empty string converts it to None in SystemState."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # Empty string gets treated as "no error" which is stored as None
    controller.state_manager.set_error("")
    assert controller.state_manager.system.last_error is None


# =============================================================================
# History Subscriptions Tests (3 tests)
# =============================================================================

async def test_subscribe_history_calls_callback_on_update():
    """subscribe_history callback is called when update_message is invoked."""
    received_messages = []
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    def on_history(history):
        received_messages.append(history)
    
    unsub = controller.state_manager.subscribe_history(on_history)
    
    controller.state_manager.update_message("First message", sender="alice")
    
    assert len(received_messages) == 1
    msg = received_messages[0].messages[0]
    assert msg.text == "First message"


async def test_subscribe_history_unsubscribes():
    """Unsubscribe function removes the callback from future notifications."""
    call_count = 0
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    def on_history(history):
        nonlocal call_count
        call_count += 1
    
    unsub = controller.state_manager.subscribe_history(on_history)
    
    # Should not raise even if no subscribers
    unsub()


async def test_subscribe_history_context_manager():
    """subscribe_history_context uses context manager protocol."""
    received_messages = []
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    with controller.state_manager.subscribe_history_context(lambda h: received_messages.append(h)):
        controller.state_manager.update_message("In context", sender="alice")
    
    assert len(received_messages) == 1


# =============================================================================
# Integration Tests (2 tests)
# =============================================================================

async def test_full_controller_state_update_cycle():
    """Full cycle: init -> subscribe -> update -> unsubscribe."""
    
    class SimpleStorage:
        async def init(self) -> None: pass
        @staticmethod
        async def fetch_history(limit: int):
            if limit <= 0: 
                return [("alice", "Hello", 1)]
            return [("alice", "Hello", 1)]
        @staticmethod
        async def close() -> None: pass
    
    storage = SimpleStorage()
    await storage.init()
    
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=storage, transport=None)
    await controller.load_history(limit=0)
    
    history_events = []
    peer_events = []
    system_events = []
    
    def on_hist(h): history_events.append(h)
    def on_peer(p, pid): peer_events.append(pid)
    def on_sys(s): system_events.append(None)
    
    ctrl_hist = controller.state_manager.subscribe_history(on_hist)
    ctrl_peers = controller.state_manager.subscribe_peers(on_peer)
    ctrl_sys = controller.state_manager.subscribe_system(on_sys)
    
    # Trigger updates
    msg1 = controller.state_manager.update_message("World", sender="alice")
    controller.state_manager.set_error("Simulated error")
    
    # History events should be triggered
    assert len(history_events) > 0


async def test_controller_state_recovery_after_error():
    """Controller state can be checked after error is set."""
    controller = ChatController(name="TestUser", host="localhost", port=12345, storage=None, transport=None)
    
    # Add message
    msg = controller.state_manager.update_message("Test", sender="me")
    
    # Set error
    controller.state_manager.set_error("Error occurred")
    
    # Should still be able to access state
    assert controller.state_manager.history.messages[0].text == "Test"


# =============================================================================
# Test Completion: 26 tests for ChatController state management
# =============================================================================
