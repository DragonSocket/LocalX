"""Test message validation logic for ChatController."""

import pytest

import sys
sys.path.insert(0, '/home/blastmerder/Documents/projects/python/localX/src')
from controller.core import StateManager


class TestMessageValidation:
    """Tests for message validation in StateManager.update_message."""
    
    @pytest.fixture
    def sm(self) -> StateManager:
        return StateManager()
    
    # --- PASSING tests ---
    
    def test_valid_simple_message(self, sm: StateManager):
        msg = "Hello"
        result = sm.update_message(msg, "test")
        assert result.text == msg
    
    def test_valid_long_text(self, sm: StateManager):
        msg = "a" * 99
        result = sm.update_message(msg, "test")
        assert result.text == msg
    
    def test_valid_special_chars(self, sm: StateManager):
        msg = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        result = sm.update_message(msg, "test")
        assert result.text == msg
    
    # --- FAILING tests (need validation logic) ---
    
    def test_reject_none_message(self, sm: StateManager):
        with pytest.raises(ValueError, match="Message must be a string"):
            sm.update_message(None, "test")
    
    def test_reject_empty_string(self, sm: StateManager):
        with pytest.raises(ValueError, match="Message is empty"):
            sm.update_message("", "test")
    
    def test_reject_whitespace_only(self, sm: StateManager):
        with pytest.raises(ValueError, match="Message is empty"):
            sm.update_message("   ", "test")
    
    def test_reject_null_bytes(self, sm: StateManager):
        with pytest.raises(ValueError, match="Invalid characters"):
            sm.update_message("\x00\x01", "test")
    
    def test_reject_tab_newlines_only(self, sm: StateManager):
        text = "\n\t\r"
        with pytest.raises(ValueError, match="Message is empty"):
            sm.update_message(text, "test")
    
    def test_reject_oversized_message(self, sm: StateManager):
        msg = "a" * 101
        with pytest.raises(ValueError, match="Message too long"):
            sm.update_message(msg, "test")
    
    def test_reject_oversized_message_boundary(self, sm: StateManager):
        msg = "x" * 100
        result = sm.update_message(msg, "test")
        assert result.text == msg
    
    def test_reject_unicode_surrogates(self, sm: StateManager):
        text = "\udcff\ud900"
        with pytest.raises(ValueError, match="Invalid characters"):
            sm.update_message(text, "test")
    
    def test_reject_control_chars_except_tab(self, sm: StateManager):
        text = "\x0b\x0c"  # Vertical tab, form feed
        with pytest.raises(ValueError, match="Invalid characters"):
            sm.update_message(text, "test")
    
    def test_valid_emoji(self, sm: StateManager):
        msg = "Hello \U0001F600!"
        result = sm.update_message(msg, "test")
        assert result.text == msg
    
    def test_valid_mixed_content(self, sm: StateManager):
        msg = "Test 测试 тест" * 3
        result = sm.update_message(msg, "test")
        assert result.text == msg
    
    def test_reject_dangerous_chars(self, sm: StateManager):
        with pytest.raises(ValueError, match="Invalid characters"):
            sm.update_message("; rm -rf /", "test")
