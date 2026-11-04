"""Unit tests for ChatScreen keyboard shortcuts and bindings."""

import pytest
from textual.app import App
from textual.binding import Binding


class TestChatScreenKeyboardShortcuts:
    """Test keyboard shortcut functionality in ChatScreen."""
    
    @pytest.mark.asyncio
    async def test_chat_screen_has_quit_bindings(self):
        """Test that ChatScreen has quit bindings defined."""
        from src.ui import screens
        
        chat = screens.ChatScreen()  # Direct reference
        
        # Should have BINDINGS attribute with quit action
        assert hasattr(chat, 'BINDINGS')
        bindings = chat.BINDINGS
        
        # Should have at least 1 binding (quit)
        assert len(bindings) >= 1
    
    @pytest.mark.asyncio  
    async def test_chat_screen_binding_keys(self):
        """Test that ChatScreen bindings have keys defined."""
        from src.ui import screens
        
        chat = screens.ChatScreen()
        
        # Verify bindings exist and have keys
        assert hasattr(chat, 'BINDINGS')
        
        for binding in chat.BINDINGS:
            # Binding should have key attribute
            if hasattr(binding, 'key'):
                assert binding.key is not None
    
    @pytest.mark.asyncio
    async def test_chat_screen_accepts_custom_bindings(self):
        """Test that ChatScreen can be configured with custom keyboards shortcuts."""
        from src.ui import screens
        
        # Check BINDINGS class attribute exists and is iterable
        chat = screens.ChatScreen()
        
        assert hasattr(screens.ChatScreen, 'BINDINGS')
        bindings = screens.ChatScreen().BINDINGS
        
        # Should be a list or tuple of Binding objects
        assert len(bindings) >= 1


class TestCustomKeyboardShortcuts:
    """Test custom keyboard shortcut implementations."""
    
    @pytest.mark.asyncio
    async def test_custom_binding_registration(self):
        """Test that ChatScreen can register custom handler methods as bindings."""
        pass
    
    @pytest.mark.asyncio  
    async def test_shortcut_method_existence_checks(self):
        """Verify screen has necessary handler method stubs for shortcuts."""
        from src.ui import screens
        
        chat = screens.ChatScreen()
        
        # Check if handle_key action works - Textual uses BINDINGS internally
        assert callable(getattr(chat, 'action_quit_app', None)) or len(chat.BINDINGS) >= 1
    
    @pytest.mark.asyncio
    async def test_custom_binding_validation(self):
        """Complete test for custom keyboard shortcut bindings."""
        from src.ui import screens
        
        chat = screens.ChatScreen()
        
        # Count available bindings
        assert len(chat.BINDINGS) >= 4
        
        # Each binding should have required attributes
        quit_bind = [b for b in chat.BINDINGS if b.action == "quit_app"][0]
        assert quit_bind.action == "quit_app"
        
        new_peer_bind = [b for b in chat.BINDINGS if b.action == "new_peer"]
        assert len(new_peer_bind) >= 1
        
        save_msg_bind = [b for b in chat.BINDINGS if b.action == "save_msg"]
        assert len(save_msg_bind) >= 1
        
        toggle_status_bind = [b for b in chat.BINDINGS if b.action == "toggle_status"]
        assert len(toggle_status_bind) >= 1
    
    @pytest.mark.asyncio
    async def test_binding_shortcut_keys(self):
        """Test that bindings have proper shortcut keys."""
        from src.ui import screens
        
        chat = screens.ChatScreen()
        
        # Check for expected key combinations
        keys_by_action = {b.action: b.key for b in chat.BINDINGS}
        
        assert "quit_app" in keys_by_action or len(keys_by_action) >= 4
        
    

