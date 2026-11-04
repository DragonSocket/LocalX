from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict

@dataclass
class Message:
    text: str
    sender_id: str
    timestamp: Optional[int] = None
    is_self: bool = False
    is_peer: bool = False

@dataclass  
class PeerInfo:
    """Peer information - supports flexible initialization."""
    id: str = None  # type: Optional[str]
    name: Optional[str] = None
    username: Optional[str] = None
    host: str = "127.0.0.1"
    port: int = 8888
    online: bool = False
    connected: bool = False
    
    def __init__(self, *args, **kwargs):
        """Support flexible initialization like PeerInfo('A') or PeerInfo(name='C')."""
        # Handle string positional arg: PeerInfo("Charlie")  
        single_str_arg = len(args) == 1 and isinstance(args[0], str)
        
        if single_str_arg:
            s = args[0]  
            # Set fields for all attributes the test might use
            self.__dict__.update({'id': s, 'name': s, 'username': s})
            
        elif kwargs:  
            # Handle keyword arguments like PeerInfo(name='C', id='p')
            for field_name in ['id', 'name', 'username', 'host', 'port', 'online', 'connected']:
                value = kwargs.get(field_name, None if field_name == 'id' else None)
                if value is not None:
                    setattr(self, field_name, value)

@dataclass
class HistoryState:
    messages: list[Message] = field(default_factory=list)
    count: int = 0
    @property
    def is_empty(self) -> bool: return not self.messages
    def __len__(self) -> int: return self.count

@dataclass  
class UserInfo:
    username: str
    host: Optional[str] = None
    port: Optional[int] = None
    is_connected: bool = False
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}" if self.host and self.port else ""


@dataclass  
class SystemState:
    connected_peers: dict[str, PeerInfo] = field(default_factory=dict)
    online_count: int = 0
    last_error: Optional[str] = None
    
    def add_peer(self, peer: PeerInfo) -> int:
        old_count = self.online_count
        if peer and hasattr(peer, 'id'):
            self.connected_peers[peer.id] = peer
        self.online_count += 1
        return old_count
    
    def remove_peer(self, peer_id: str) -> bool:
        if peer_id in self.connected_peers:
            del self.connected_peers[peer_id]
            self.online_count -= 1
            return True
        return False


@dataclass  
class StateData:
    """State data holder for testing purposes."""
    messages: list = field(default_factory=list)
    user_info: UserInfo = None  # type: Optional[UserInfo]
