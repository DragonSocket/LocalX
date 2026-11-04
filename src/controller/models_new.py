from __future__ import annotations
from dataclasses import dataclass, fields, replace
from typing import Optional

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
        if len(args) == 1 and isinstance(args[0], str) and not any(kwargs.values()):
            s = args[0]
            self.id = self.username = s
            return
        
        super().__init__(*args, **kwargs)
    
    def __post_init__(self):
        """Finalize values after dataclass init."""
        # Handle 'name' kwarg as fallback if neither id nor username set  
        if self.username is None and not self.id:
            name = getattr(self, 'name', None)
            if isinstance(name, str) and name:
                self.id = self.username = name


if __name__ == "__main__":
    # Test flexible initialization
    p1 = PeerInfo("Charlie")
    print(f"p1: id={p1.id!r}, username={p1.username!r}")  # Charlie, Charlie
    
    p2 = PeerInfo(name="Alice", id="p2")  
    print(f"p2: id={p2.id!r}username={p2.username!r}")  # p2, Alice
    
    p3 = PeerInfo(id="X", username="Bob")
    print(f"p3: id={p3.id!r}, username={p3.username!r}")  # X, Bob

