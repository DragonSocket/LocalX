"""State management with event subscription support."""
from __future__ import annotations
import uuid
from typing import Optional, Callable, Any

from src.controller.models import HistoryState, PeerInfo, SystemState, Message, UserInfo, StateData


class _CallbackHolder:
    """Wrapper ensuring each subscription gets unique identity object."""
    __slots__ = ('_id', '_callback')

    def __init__(self, callback):
        self._id = "ch_" + uuid.uuid4().hex[:8] 
        self._callback = callback
    
    def __call__(self, *args, **kwargs) -> Any:
        return self._callback(*args, **kwargs) 
    
    def __repr__(self):
        func_name = getattr(self._callback, '__name__', str(type(self._callback)))
        return f"_CallbackHolder(id={getattr(self, '_id', 'unset')}, func=<{func_name}>)"


class SubBase:
    """Base class for subscriptions with cleanup and context-manager support."""
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


class HistorySub(SubBase):  # History subscription with context-manager support
    """History event subscriber that uses SubBase for cleanup."""
    pass

class PeerSub(SubBase):  # Peer subscription with context-manager support  
    """Peer event subscriber that uses SubBase for cleanup."""
    pass

class SystemSub(SubBase):  # System subscription with context-manager support    
    """System event subscriber with context-manager support."""
    pass


class StateManager:
    """
    Manages state with event subscriptions using unique identity tracking.
    
    Key behaviors:
    - Each subscribe_* call creates unique wrapper instance for that registration
    - Wrappers stored per manager in private lists  
    - All managers use a SINGLETON shared HistoryState object (singleton compatible)
    - Unsubscribe uses identity check so same function can be subscribed multiple times separately
    """

    # Singleton shared state storage - used by all manager instances  
    _SHARED_HISTORY = None

    def __init__(self):
        self._history_callbacks: list = []  
        self._peer_callbacks: list = []
        self._system_callbacks: list = []
        
        # Get or create singleton shared history for all managers
        if StateManager._SHARED_HISTORY is None:
            # Create new singleton history once - first manager does it
            h = HistoryState()
            StateManager._SHARED_HISTORY = h
        self._shared_history = StateManager._SHARED_HISTORY
    
    @property
    def history(self) -> HistoryState:
        """Return singleton shared history state."""
        return StateManager._SHARED_HISTORY

    @property
    def info(self) -> UserInfo: