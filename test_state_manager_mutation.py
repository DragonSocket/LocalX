import asyncio
import uuid
from unittest.mock import Mock

class _CallbackHolder:
    __slots__ = ('_callback', '_type', 'uuid')
    def __init__(self, callback, event_type):
        self._callback = callback
        self._type = event_type
        self.uuid = uuid.uuid4()
    def __call__(self, *args, **kwargs): return self._callback(*args, **kwargs)

class HistoryState:
    def __init__(self, messages=None):
        self.messages = messages if messages else []
        self.info = None

class SystemState:
    def __init__(self, connected_peers=None, online_count=0, last_error=None):
        self.connected_peers = connected_peers if connected_peers else {}
        self.online_count = online_count
        self.last_error = last_error

class UserInfo:
    def __init__(self, username):
        self.username = username

class StateManager:
    _shared_registry = {}
    def __init__(self):
        self._history_callbacks = []
        self._peer_callbacks = []
        self._system_callbacks = []
        self._shared_history = HistoryState()
        self._sys_state = SystemState()
        self._info_initialized = False

    def _make_unsub(self, holder):
        holder_id = holder.uuid
        history_list = self._history_callbacks
        peer_list = self._peer_callbacks
        system_list = self._system_callbacks
        def unsub():
            if holder_id in StateManager._shared_registry:
                handlers_list = StateManager._shared_registry[holder_id]
                for i, h in enumerate(handlers_list):
                    if h.uuid == holder_id:
                        handlers_list.pop(i)
                        break
                if not handlers_list:
                    del StateManager._shared_registry[holder_id]
            for callback_list in [history_list, peer_list, system_list]:
                for i, h in enumerate(callback_list):
                    if h.uuid == holder_id:
                        callback_list.pop(i)
                        break
        return unsub

    def subscribe_history(self, callback):
        holder = _CallbackHolder(callback, 'history')
        if holder.uuid not in StateManager._shared_registry:
            StateManager._shared_registry[holder.uuid] = []
        StateManager._shared_registry[holder.uuid].append(holder)
        self._history_callbacks.append(holder)
        return self._make_unsub(holder)

    def _notify_history_callbacks(self):
        for holder_list in list(StateManager._shared_registry.values()):
            for holder in list(holder_list):
                try:
                    holder(self._shared_history)
                except Exception:
                    pass

async def test_mutation_during_iteration():
    sm = StateManager()
    
    # This callback will unsubscribe ITSELF when called
    def self_unsubscribing_callback(state):
        unsub()
    
    unsub = sm.subscribe_history(self_unsubscribing_callback)
    
    # Trigger notification - this should not raise RuntimeError
    try:
        sm._notify_history_callbacks()
        print("Mutation test passed!")
    except RuntimeError as e:
        print(f"Mutation test FAILED: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(test_mutation_during_iteration())
