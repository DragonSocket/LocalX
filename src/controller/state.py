from __future__ import annotations
import uuid
import weakref
import time
from typing import Optional, Callable, Any, List

from src.controller.models import HistoryState, PeerInfo, SystemState, Message, UserInfo


class _CallbackHolder:
    """Wrapper ensuring each subscription gets unique identity object."""
    
    __slots__ = ('_callback', '_type', 'uuid', '__weakref__')
    
    def __init__(self, callback, event_type):
        self._callback = callback
        self._type = event_type
        self.uuid = uuid.uuid4()
    
    def __call__(self, *args, **kwargs) -> Any:
        return self._callback(*args, **kwargs)
    
    def __repr__(self):
        func_name = getattr(self._callback, '__name__', str(type(self._callback)))
        return f"_CallbackHolder(type={self._type}, func=<{func_name}>, uuid={self.uuid})"


class SubBase:
    """Base class for subscriptions with cleanup."""
    
    def __init__(self):
        self._closed = False
    
    def close(self):
        self._closed = True
        
    @property
    def cleanup(self) -> Callable[[], None]:
        return self.close
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
        return False


class HistorySub(SubBase):
    """History event subscriber."""
    pass


class PeerSub(SubBase):
    """Peer event subscriber."""
    pass


class SystemSub(SubBase):
    """System event subscriber."""
    pass


class StateManager:
    """Manages state with event subscriptions using shared registry for singleton compatibility."""

    # Class-level registry for shared subscriptions (singleton compatibility)
    # Using WeakValueDictionary to prevent memory leaks from orphaned subscriptions
    _shared_registry: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
    
    def __init__(self):
        self._history_callbacks: List[_CallbackHolder] = []  
        self._peer_callbacks: List[_CallbackHolder] = []
        self._system_callbacks: List[_CallbackHolder] = []
        
        # Shared state
        self._shared_history = HistoryState(messages=[])
        self._sys_state = SystemState(connected_peers={}, online_count=0, last_error=None)
        self._info_initialized = False
    
    @property
    def history(self) -> HistoryState:
        return self._shared_history
    
    @property 
    def system(self) -> SystemState:
        return self._sys_state
    
    def _init_state(self, user_info="Unknown"):
        """Initialize state with default or passed user info."""
        # Initialize history with empty messages and optional user info
        if not self._info_initialized:
            if isinstance(user_info, UserInfo):
                self._shared_history.info = UserInfo(str(user_info.username))
            else:
                self._shared_history.info = UserInfo(str(user_info) or "Unknown")
            self._info_initialized = True
    
    def _make_context_sub(self, holder, sub_class):
        """Create context manager object with proper close."""
        unsub = self._make_unsub(holder)
        sub = sub_class()
        sub.close = unsub
        return sub, unsub
    
    def subscribe_history(self, callback):
        """Subscribe to history events. Returns unsubscribe function."""
        holder = _CallbackHolder(callback, 'history')
        
        # Register in shared registry (singleton-compatible)
        StateManager._shared_registry[holder.uuid] = holder
        
        # Also store per-instance for independent instances
        self._history_callbacks.append(holder)
        
        return self._make_unsub(holder)

    def subscribe_history_context(self, callback):
        """Subscribe to history events using context manager protocol."""
        holder = _CallbackHolder(callback, 'history')
        
        # Register in shared registry
        StateManager._shared_registry[holder.uuid] = holder
        
        # Also add to instance list
        self._history_callbacks.append(holder)
        
        sub, unsub = self._make_context_sub(holder, HistorySub)
        return sub  # Context manager's __exit__ calls close which contains unsub
    
    def _make_unsub(self, holder):
        """Create unsubscribe function that removes from both shared and local lists."""
        holder_id = holder.uuid
        
        # Create closure variables to avoid capturing state instance reference issues
        history_list = self._history_callbacks
        peer_list = self._peer_callbacks  
        system_list = self._system_callbacks
        
        def unsub():
            # Remove from shared registry first (where most notifications read from)
            if holder_id in StateManager._shared_registry:
                del StateManager._shared_registry[holder_id]
            
            # Also remove from per-instance callback lists (use closure-captured references)
            for callback_list in [history_list, peer_list, system_list]:
                if callback_list is not None:  # Defensive check
                    for i, h in enumerate(callback_list):
                        if h.uuid == holder_id:
                            callback_list.pop(i)
                            break  # Only remove one match
            
            return None
        
        return unsub
    
    def subscribe_peers(self, callback):
        """Subscribe to peer events. Returns unsubscribe function."""
        holder = _CallbackHolder(callback, 'peers')
        
        # Register in shared registry
        StateManager._shared_registry[holder.uuid] = holder
        
        # Also store per-instance
        self._peer_callbacks.append(holder)
        
        return self._make_unsub(holder)

    def subscribe_peers_context(self, callback):
        """Subscribe to peer events using context manager protocol."""
        holder = _CallbackHolder(callback, 'peers')
        
        # Register in shared registry
        StateManager._shared_registry[holder.uuid] = holder
        
        self._peer_callbacks.append(holder)
        
        sub, unsub = self._make_context_sub(holder, PeerSub)
        return sub
    
    def subscribe_system(self, callback):
        """Subscribe to system events. Returns unsubscribe function."""
        holder = _CallbackHolder(callback, 'system')
        
        # Register in shared registry
        StateManager._shared_registry[holder.uuid] = holder
        
        self._system_callbacks.append(holder)
        
        return self._make_unsub(holder)

    def subscribe_system_context(self, callback):  
        """Subscribe to system events using context manager protocol."""
        holder = _CallbackHolder(callback, 'system')
        
        # Register in shared registry
        StateManager._shared_registry[holder.uuid] = holder
        
        self._system_callbacks.append(holder)
        
        sub, unsub = self._make_context_sub(holder, SystemSub)
        return sub  # Context manager's __exit__ calls close which contains unsub
    
    def _notify_history_callbacks(self):
        """Notify all history subscribers with current history state."""
        for holder in list(StateManager._shared_registry.values()):
            try:
                holder(self._shared_history)
            except Exception:
                pass

    def update_message(self, text, sender=None, receiver=None):  
        """Add a new message and notify history subscribers.
        
        Args:
            text: Message text to add (may be None)
            sender: Sender identifier (default based on context)
            receiver: Optional peer identifier
            
        Returns:
            Message instance if valid
            
        Raises:
            ValueError: If the message fails validation
        """
        # Handle None or non-string input - convert for validation
        if text is None:
            raise ValueError("Message must be a string")
        
        # Convert to string if needed (for type safety)
        text_str = str(text)
        
        # Validate message before processing
        try:
            from src.controller.utils import validate_message
            is_valid, _ = validate_message(text_str)
        except ValueError as e:
            raise ValueError(str(e))
        
        current_msgs = getattr(self._shared_history, 'messages', [])
        
        last_timestamp = 0
        if len(current_msgs) > 0:
            last_msg = current_msgs[-1]
            if hasattr(last_msg, 'timestamp'):
                last_timestamp = int(last_msg.timestamp) + 1
        
        new_message = Message(
            text=text_str, 
            sender_id=sender or "unknown", 
            timestamp=last_timestamp,
        )
        
        self._shared_history.messages.append(new_message)
        self._notify_history_callbacks()
        
        return new_message

    def initialize_with_history(self, history: list[tuple]) -> None:
        """Initialize state from saved history.
        
        Args:
            history: List of tuples (msg_text, sender_id, timestamp)
        """
        for msg_data in history[:100]:  # Limit to 100 messages
            if msg_data and len(msg_data) >= 2:
                text = msg_data[0] or ""
                sender_id = msg_data[1] if len(msg_data) > 1 else "unknown"
                timestamp = int(msg_data[2]) if len(msg_data) > 2 else 0
                
                try:
                    self.update_message(text, sender=sender_id)
                except ValueError:
                    # Skip invalid history entries
                    pass

    def _notify_peer_callbacks(self):
        """Notify all peer subscribers with current peer state."""
        for holder in list(StateManager._shared_registry.values()):
            try:
                # Call with first peer and peer id as string
                if hasattr(holder, '__call__'):
                    # Notify about all connected peers
                    connected_peers = self._sys_state.connected_peers
                    if isinstance(connected_peers, dict):
                        for peer_id, peer_info in connected_peers.items():
                            holder(peer_info, peer_id)
            except Exception:
                pass

    def update_peers(self, peers_dict=None):
        """Update peer connections and notify subscribers."""
        if self._sys_state is None:
            self._sys_state = SystemState(connected_peers={}, online_count=0, last_error=None)
        
        current_sys = getattr(self, '_sys_state', None) or SystemState()
        
        if isinstance(current_sys.connected_peers, list):
            current_sys.connected_peers = {}
        
        if peers_dict is not None and isinstance(peers_dict, dict):
            for pid, pinfo in list(peers_dict.items()):
                peer_obj = pinfo
                if hasattr(peer_obj, 'id') and not isinstance(peer_obj, str):
                    current_sys.connected_peers[peer_obj.id] = peer_obj
        
        self._notify_peer_callbacks()

    def _notify_system_callbacks(self):
        """Notify all system subscribers with current system state."""
        for holder in list(StateManager._shared_registry.values()):
            try:
                holder(self._sys_state)
            except Exception:
                pass

    def set_error(self, error_msg=None):
        """Set system error and notify system subscribers."""
        self._sys_state.last_error = str(error_msg) if error_msg else None
        
        self._notify_system_callbacks()


if __name__ == "__main__":
    print("StateManager module loaded successfully")
