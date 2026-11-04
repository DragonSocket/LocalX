"""Tests for event subscription/unsubscription in StateManager."""
import pytest
from src.controller.state import StateManager
from src.controller.models import (
    HistoryState, PeerInfo, SystemState, UserInfo
)


class TestEventManagerSubscription:
    """Test cases for event subscription mechanism."""

    def test_subscribe_history(self):
        """Subscribe to history events returns unsubscribe function."""
        state = StateManager()
        
        received = []
        
        def handler(history):
            received.append(history)
        
        unsub = state.subscribe_history(handler)
        assert callable(unsub)
    
    def test_history_callback_instantly_callable(self):
        """Initial state update should trigger callback."""
        state = StateManager()
        state._init_state(UserInfo("Alice"))
        
        updates = []
        
        def handler(history):
            updates.append(("new", len(history.messages)))
        
        unsub = state.subscribe_history(handler)
        state.update_message("Hello", "me", None)
        
        assert len(updates) == 1
    
    def test_unsubscribe_works(self):
        """Unsubscribe removes callback from future events."""
        state = StateManager()
        state._init_state(UserInfo("Bob"))
        
        updates = []
        
        def handler(history):
            updates.append(True)
        
        unsub = state.subscribe_history(handler)
        state.update_message("msg1", "me", None)
        unsub()
        state.update_message("msg2", "me", None)  # Should not trigger
        
        assert len(updates) == 1
    
    def test_subscribe_peers(self):
        """Subscribe to peer events returns unsubscribe function."""
        state = StateManager()
        
        received = []
        
        def handler(peer, pid):
            received.append((peer.name, pid))
        
        unsub = state.subscribe_peers(handler)
        assert callable(unsub)
    
    def test_peer_callback_instantly_callable(self):
        """Initial peer update should trigger callbacks."""
        state = StateManager()
        state._init_state(UserInfo("Alice"))
        
        updates = []
        
        def handler(peer, pid):
            updates.append((peer.name, pid))
        
        unsub = state.subscribe_peers(handler)
        state.update_peers({
            "p1": PeerInfo(name="Charlie", online=True, connected=True)
        })
        
        assert len(updates) == 1
    
    def test_peer_unsubscribe_works(self):
        """Unsubscriber for peers works correctly."""
        state = StateManager()
        
        updates = []
        
        def handler(peer, pid):
            updates.append(True)
        
        unsub = state.subscribe_peers(handler)
        state.update_peers({"p1": PeerInfo("A")})
        unsub()
        state.update_peers({"p2": PeerInfo("B")})  # Should not trigger
        
        assert len(updates) == 1
    
    def test_subscribe_system(self):
        """Subscribe to system events returns unsubscribe function."""
        state = StateManager()
        
        received = []
        
        def handler(state_obj):
            received.append(bool(state_obj.last_error))
        
        unsub = state.subscribe_system(handler)
        assert callable(unsub)
    
    def test_system_callback_instantly_callable(self):
        """Initial error should trigger callback."""
        state = StateManager()
        state._init_state(UserInfo("Test"))
        
        updates = []
        
        def handler(state_obj):
            updates.append(state_obj.last_error)
        
        unsub = state.subscribe_system(handler)
        state.set_error("Test error")
        
        assert len(updates) == 1
    
    def test_system_unsubscribe_works(self):
        """Unsubscriber for system events works correctly."""
        state = StateManager()
        
        updates = []
        
        def handler(state_obj):
            updates.append(True)
        
        unsub = state.subscribe_system(handler)
        state.set_error("first")
        unsub()
        state.set_error("second")  # Should not trigger
        
        assert len(updates) == 1
    
    def test_multiple_subscribers(self):
        """Multiple callbacks all receive updates until unsubscribed."""
        state = StateManager()
        
        subscriber_a = []
        subscriber_b = []
        
        def handler_a(history):
            subscriber_a.append("A")
        
        def handler_b(history):
            subscriber_b.append("B")
        
        unsub_a = state.subscribe_history(handler_a)
        unsub_b = state.subscribe_history(handler_b)
        
        state.update_message("test", "me", None)
        
        assert len(subscriber_a) == 1
        assert len(subscriber_b) == 1
    
    def test_multiple_unsubscribes(self):
        """First unsubscribe affects the right callback."""
        state = StateManager()
        state._init_state(UserInfo("X"))
        
        updates = []
        
        def handler(history):
            updates.append(True)
        
        unsub1 = state.subscribe_history(handler)  # Should fire for msg b
        unsub2 = state.subscribe_history(handler)  # Same function
        
        state.update_message("a", "me", None)  # Both fire -> 2 updates
        assert len(updates) == 2
        
        unsub1()  # Remove first subscriber
        state.update_message("b", "me", None)  # Should have 1 more from unsub2 only, not unsub1
        assert len(updates) == 3  # Total = 2 + 1 = 3
        
    def test_context_manager_subscription(self):
        """Subscribe should optionally use context manager protocol."""
        state = StateManager()
    
        updates = []
        
        with state.subscribe_history_context(lambda h: updates.append(True)) as unsub:
            state.update_message("mid", "me", None)
            assert len(updates) == 1
    
        state.update_message("after", "me", None)
        # After exiting context, subscription should be removed
        # So this shouldn't trigger anything -> 2 total (initial implicit setup + mid)
        assert len(updates) == 1
        
    def test_state_manager_is_singleton_compatible(self):
        """StateManager can be instantiated multiple times independently."""
        state1 = StateManager()
        state2 = StateManager()
        
        updates_global = []
        local_updates = []
        
        def handler(history):
            if history is state1.history:
                local_updates.append(True)
            else:
                updates_global.append(True)
        
        unsub = state1.subscribe_history(handler)
        
        state1.update_message("m1", "me", None)
        assert len(local_updates) == 1
        
        state2.update_message("m2", "other", None)
        assert len(updates_global) == 1
    
    def test_callback_called_with_correct_signature(self):
        """Callbacks receive correct arguments based on event type."""
        state = StateManager()
        
        history_sig = []
        peer_sig = []
        system_sig = []
        
        def check_history(history):
            history_sig.append(type(history).__name__)
        
        def check_peer(peer, pid):
            peer_sig.append((peer.name, type(pid).__name__))
        
        def check_system(system):
            system_sig.append(("SystemState", bool(system.last_error)))
        
        state.subscribe_history(check_history)
        state.subscribe_peers(check_peer)
        state.subscribe_system(check_system)
        
        state.update_message("m1", "me", None)
        assert history_sig == ["HistoryState"]
        
        state.update_peers({"p": PeerInfo("A")})
        assert peer_sig == [("A", "str")]
        
        state.set_error("err")
        assert system_sig == [("SystemState", True)]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
