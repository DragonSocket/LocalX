import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.ui.chat_app import ChatApp
from src.storage.sqlite import SqliteStorage
from src.transport.ncat import NcatTransport
from src.controller.core import ChatController
from src.ui.setup_screen import SetupSubmitted

class MockStorage:
    def __init__(self): self.init_called = False
    async def init(self): self.init_called = True
    async def save(self, u, m, t=None): return True
    async def fetch_history(self, l): return []
    async def close(self): pass

@pytest.mark.asyncio
async def test_dependency_injection_wiring():
    """
    Verify that VEGAChatApp correctly wires up dependencies
    when SetupSubmitted is received.
    """
    # Mock dependencies
    storage = MockStorage()
    
    from src.main import VEGAChatApp
    
    app = VEGAChatApp(storage=storage)
    
    # Simulate SetupSubmitted
    message = SetupSubmitted(host="127.0.0.1", port=9999)
    
    # Mock push_screen to intercept the ChatScreen
    app.push_screen = MagicMock()
    
    # Mock NcatTransport to avoid real subprocess/ncat
    with patch("src.main.NcatTransport") as MockNcat:
        # Create a mock instance that simulates what NcatTransport does
        mock_transport_instance = MagicMock(spec=NcatTransport)
        MockNcat.return_value = mock_transport_instance
        
        await app.on_setup_submitted(message)
        
        # 1. Check if NcatTransport was called with correct host/port
        MockNcat.assert_called_once_with("127.0.0.1", 9999)
        
        # 2. Check if push_screen was called with a ChatScreen
        from src.ui.chat_screen import ChatScreen
        args, _ = app.push_screen.call_args
        chat_screen = args[0]
        
        assert isinstance(chat_screen, ChatScreen)
        
        # 3. Verify the injected dependencies in ChatScreen and Controller
        assert chat_screen.transport == mock_transport_instance
        assert chat_screen.storage == storage
        assert chat_screen.controller.transport == mock_transport_instance
        assert chat_screen.controller.storage == storage
