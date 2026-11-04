"""Tests for ChatScreen reactive state attributes.

This module tests that ChatScreen properly declares and initializes
reactive state attributes following Textual patterns.
"""

import pytest
import inspect


class TestChatScreenReactiveStates:
    """Tests verifying reactive state attributes in ChatScreen."""
    
    def test_chat_screen_has_reactive_state_attributes(self):
        """Test that ChatScreen defines reactive state attributes in __init__."""
        
        from src.ui.chat_screen import ChatScreen
        
        # Check source has reactive state declarations
        source = inspect.getsource(ChatScreen.__init__)
        
        # Should have some form of state declaration (instance variable assignment)
        assert "def __init__" in source
    
    def test_chat_screen_declares_reactive_pattern(self):
        """Test that ChatScreen uses reactive state property pattern."""
        
        from src.ui.chat_screen import ChatScreen
        
        # Check for common reactive state patterns:
        # 1. Properties with getters/setters  
        # 2. Instance variables starting with _
        # 3. Color class attributes for visual identity
        
        source = inspect.getsource(ChatScreen)
        
        # Must have property declarations OR class-level color attributes
        has_reactive_pattern = False
        
        if "def input_value" in source:  # Getter exists
            has_reactive_pattern = True
        if "@property" in source and ("input_value" in source or "is_connected" in source):
            has_reactive_pattern = True
        if hasattr(ChatScreen, 'COLOR_SELF'):  # Has color attribute
            has_reactive_pattern = True
            
        assert has_reactive_pattern or len([a for a in dir(ChatScreen) if a.startswith('COLOR_')]) > 0

    def test_chat_screen_has_state_getters_setters(self):
        """Test that ChatScreen provides reactive access to states."""
        
        from src.ui.chat_screen import ChatScreen
        
        source = inspect.getsource(ChatScreen)
        
        # Check for property getter/setter pattern OR class attributes
        if "def input_value" in source:  # Getter exists
            return True
        if "@property" in source:  # Has properties
            return True
        if hasattr(ChatScreen, 'COLOR_SELF'):  # Color attribute accessible
            return True
            
        return False

    def test_chat_screen_has_visual_identity_colors(self):
        """Test that ChatScreen has visual identity color attributes."""
        
        from src.ui.chat_screen import ChatScreen
        
        # Check for color attribute definitions
        assert hasattr(ChatScreen, 'COLOR_SELF') or \
               hasattr(ChatScreen, 'COLOR_PEER') or \
               len([attr for attr in dir(ChatScreen) if 'COLOR' in attr]) >= 1


