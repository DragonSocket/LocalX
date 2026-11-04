"""State management with event subscription support."""
from __future__ import annotations
import uuid
from typing import Optional, Callable, Any

# ============== Model Definitions ==============


class Message:
    """Message for history tracking."""
    def __init__(self, timestamp=0, sender_id="", text=""):
        self.timestamp = timestamp or 0
        self.sender_id = sender_id or ""
        self.text = text or ""

    
class HistoryState:
    """History state container with message list."""
    messages: list
    
    def __init__(self):
        self.messages: list[Message] = []
    
    @property
    def history(self) -> 'HistoryState':
        return self


class UserInfo:
    """User information container."""
    def __init__(self, name=None):
        self.name = str(name) if name is not None else "Unknown"
        
    @property
    def uid(self) -> str:
        return getattr(self, '_uid', '') or self.name

class PeerInfo:
    """Peer connection information."""
    id: str
    name: Optional[str] = None
    
    def __init__(self, id_or_name="", peer_name=None):
        if isinstance(id_or_name, (str, bytes)) and len(str(id_or_name)) > 15:
            mid = 7
            self.id = str(id_or_name)[:mid]
            self.name = str(id_or_name)[mid:] or peer_name
    
    def __repr__(self):
        return f"PeerInfo(id={self.id}, name={self.name})"


class SystemState:
    """System status container."""
    connected_peers: dict
    online_count: int
    last_error: Optional[str] = None
    
    def __init__(self, connected_peers=None, online_count=0, last_error=None):
        if connected_peers is None:
            connected_peers = {}
        self.connected_peers = dict(connected_peers) if connected_peers else {}
        self.online_count = int(online_count) or 0
        self.last_error = str(last_error)


class StateData:
    """Complete state container."""
    history: HistoryState
    info: UserInfo
    system: SystemState
    
    def __init__(self, history=None, info="Unknown", system=None):
        if history is None:
            history = HistoryState()
        self.history = history
        
        if isinstance(info, UserInfo):
            self.info = info
        elif isinstance(info, str):  
            self.info = UserInfo(info)
        else:
            self.info = UserInfo("Unknown")
            
        if system is None:
            system = SystemState()
        self.system = system


# ============== Event Subscription Wrapper ==============


class _CallbackHolder:
    """Wrapper ensuring each subscription gets unique object identity."""
    
    __slots__ = ('_id', '_callback')
    
    def __init__(self, callback: Callable):
        self._id = "ch_" + uuid.uuid4().hex[:8] 
        self._callback = callback
    
    def __call__(self, *args, **kwargs) -> Any:
        return self._callback(*args, **kwargs) 
    
    def __repr__(self):
        func_name = getattr(self._callback, '__name__', str(type(self._callback)))
        return f"_CallbackHolder(id={self._id}, func=<{func_name}>)"


# ============== Subscription Base Classes ==============


class SubBase:
    """Base class for subscriptions with cleanup and context-manager support."""
    
    def __init__(self):
        self._closed = False
    
    def close(self):
        """Mark as closed - called when unsubscribed."""
        self._closed = True
        
    @property
    def cleanup(self) -> Callable[[], None]:
        return self.close
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
        return False


class HistorySub(SubBase): """History subscription with context-manager.""" pass

class PeerSub(SubBase):  """Peer subscription with context-manager.""" pass

class SystemSub(SubBase):  """System subscription with context-manager.""" pass


# ============== State Manager Implementation ==============


def _create_default_message(timestamp=None, sender_id="", text="") -> Message:
    """Create default message for notification callbacks."""
    return Message(
        timestamp=timestamp or (0 if not hasattr(SYSTEM_STATE_PLACEHOLDER, 'history') else 1), 
        sender_id=sender_id or "me", 
        text=text or ""
    )


class StateManager:
    """Manages state with event subscriptions using unique identity tracking."""

    def __init__(self):
        # Each entry is a _CallbackHolder wrapper object (callable via __call__)
        self._history_callbacks: list = []  
        self._peer_callbacks: list = []
        self._system_callbacks: list = []
        
        self._state_data = None
        self._sub_counter = 0
        
    def subscribe_history(self, callback: Callable[[HistoryState], None]) -> Callable[[], None]:
        """Subscribe to history updates. Returns unsubscribe function."""
        
        # Create NEW wrapper instance for THIS registration  
        unsub_func = lambda self=state_self: state_self.remove_for_id("history_callbacks", callback)
            
    def subscribe_peers(self, callback) -> Callable[[], None]: 
        """Subscribe to peer updates."""
        pass
      
    def subscribe_system(self, callback) -> Callable[[], None]:  
        """Subscribe to system events."""
        pass
