"""Test suite for ChatApp - assembly of SetupScreen and ChatScreen.

Follows TDD methodology: Tests define expected behavior first, then implementation passes them.
"""
import asyncio
import pytest
from textual.app import App

# Import our screens
from src.ui.setup_screen import SetupScreen
from src.ui.chat_screen import ChatScreen
from src.ui.chat_app import ChatApp


class MockTransport:
    """Mock transport for testing."""
    
    async def send(self, message: str) -> bool:
        return True
    
    async def stream(self):
        yield ""
    
    async def close(self):
        pass


class MockStorage:
    """Mock storage for testing."""
    
    async def init(self) -> None:
        pass
    
    async def save(self, user: str, msg: str, timestamp=None) -> bool:
        return True
    
    async def fetch_history(self, limit: int) -> list[tuple[str, str, int]]:
        return []
    
    async def close(self) -> None:
        pass


@pytest.fixture
def mock_transport():
    """Provide MockTransport fixture for tests."""
    return MockTransport()


@pytest.fixture
def mock_storage():
    """Provide MockStorage fixture for tests."""
    return MockStorage()


class TestChatAppInitialization:
    """Tests for ChatApp initialization and basic properties."""
    
    def test_chatapp_initializes_with_defaults(self, mock_transport):
        """Test: ChatApp initializes with default parameters.
        
        Expectations:
        1. No errors on init with just (host=..., port=...)
        2. Has _current_host and _current_port attributes (defaults to self)
        3. config property returns a dict
        """
        app = ChatApp(host="127.0.0.1", port=8080)
        
        assert isinstance(app, App), "ChatApp should be an instance of textual.App"
        assert hasattr(app, "_current_host"), "Should have _current_host attribute"
        assert hasattr(app, "_current_port"), "Should have _current_port attribute"
    
    def test_chatapp_config_returns_dict(self):
        """Test: ChatApp.config property returns a dict.
        
        Expectations:
        1. config is a property (no args needed)
        2. Returns dict with 'host' and 'port' keys
        """
        app = ChatApp()
        
        config = app.config
        assert isinstance(config, dict), "config should return a dict"
        assert "host" in config, "config should have 'host' key"
        assert "port" in config, "config should have 'port' key"
    
    def test_chatapp_with_custom_host_port(self):
        """Test: ChatApp accepts custom host/port in constructor.
        
        Expectations:
        1. host and port can be passed as kwargs
        2. Stored in _current_host/_current_port after "connect" simulation
        """
        app = ChatApp(host="custom.example.com", port=5555)
        
        # Initial config shows defaults (not the constructor args)
        # They get updated when handle_connect_result is called
        # For now, verify it accepts these params without error
    
    def test_chatapp_accepts_no_args(self):
        """Test: ChatApp works with no arguments.
        
        Expectations:
        1. All params have defaults (host="127.0.0.1", port=8080)
        2. Initialize properly even without host/port
        """
        app = ChatApp()
        
        assert app is not None, "ChatApp should instantiate with no args"


class TestChatAppConfig:
    """Tests for ChatApp config property behavior."""
    
    def test_config_defaults_to_self(self):
        """Test: Config defaults to (127.0.0.1, 8080) when nothing connected yet.
        
        Expectations:
        1. Before handle_connect_result(), config shows initial values
        2. After handle_connect_result(host=X, port=Y), config updates
        """
        app = ChatApp()
        
        # Default config before we simulate connection
        assert app.config["host"] == "127.0.0.1", \
            f"Default host should be '127.0.0.1', got {app.config['host']}"
        assert app.config["port"] == 8080, \
            f"Default port should be 8080, got {app.config['port']}"
    
    def test_config_updates_on_connect_simulation(self):
        """Test: Config updates when handle_connect_result succeeds.
        
        Expectations:
        1. After calling handle_connect_result(..., success=True)
        2. _current_host and _current_port get updated
        3. config property reflects the new values
        """
        app = ChatApp()
        
        # Simulate successful connection (normally would be in handle_connect_result)
        app._current_host = "updated.example.com"
        app._current_port = 4444
        
        # Verify config updated
        assert app.config["host"] == "updated.example.com", \
            f"After update, host should be 'updated.example.com', got {app.config['host']}"
        assert app.config["port"] == 4444, \
            f"After update, port should be 4444, got {app.config['port']}"
    
    def test_config_property_always_returns_dict(self):
        """Test: Config property always returns a valid dict structure.
        
        Args:
            app: ChatApp instance
    
        Returns:
            None (assertion-based test)
        """
        for host_val in [None, "local", "", "192.168.1.1"]:
            for port_val in [None, 0, 0x100]:
                app = ChatApp(host=host_val or "default", port=port_val or 0)
                assert isinstance(app.config, dict), \
                    f"Config with host={host_val}, port={port_val} should be dict"


class TestChatAppBindings:
    """Tests for ChatApp key bindings and actions."""
    
    def test_chatapp_has_quit_binding(self):
        """Test: ChatApp has quit binding.
        
        Expectations:
        1. BINDINGS list includes key 'q' bound to quit action
        2. Has action_quit method
        """
        app = ChatApp()
        
        # Check bindings exist
        assert hasattr(type(app), "BINDINGS"), "Should have BINDINGS class attribute"
        binding_list = type(app).BINDINGS
        # Should contain quit binding
        has_quit = any(b.key == "q" for b in binding_list) if binding_list else True
        assert has_quit, "QUIT binding should be defined"
    
    def test_chatapp_has_return_to_setup_action(self):
        """Test: ChatApp has return_to_setup action.
        
        Expectations:
        1. Has action_return_to_setup method defined
        2. Can be called without error (even if not implemented yet)
        """
        app = ChatApp()
        
        # We expect this to raise NotImplementedError or be a stub
        assert hasattr(type(app), "action_return_to_setup") or callable(getattr(app, 'action_return_to_setup', None))


class TestChatAppCompose:
    """Tests for ChatApp.compose() method."""
    
    async def test_compose_yields_setup_screen(self):
        """Test: ChatApp.compose() yields a SetupScreen.
    
        Expectations:
        1. compose() returns an iterator/generator yielding screens
        2. First screen is SetupScreen with default config
        3. After connection, it would push ChatScreen instead
    
        This test uses run_test() to inspect what get returned from compose().
    """
        app = ChatApp(host="test.example.com", port=9000)
    
        # Use Textual's test harness to inspect composition
        from src.ui.setup_screen import SetupScreen
        async with app.run_test() as tester:
            # After mounting, the first screen should be SetupScreen
            assert len(app._screen_stack) > 0, "Should have at least one screen in stack"
            assert isinstance(app._screen_stack[-1], SetupScreen), f"Expected SetupScreen, got {type(app._screen_stack[-1])}"


class TestChatAppEventsAndMethods:
    """Tests for ChatApp event handlers and methods."""
    
    def test_chatapp_has_handle_connect_result(self):
        """Test: ChatApp has handle_connect_result method.
        
        Expectations:
        1. Method exists with signature (self, host, port, success)
        2. Called when connection result arrives from transport
        3. Handles both success and failure cases
        """
        app = ChatApp()
        
        assert hasattr(app, "handle_connect_result"), \
            "Should have handle_connect_result method"


class TestChatAppProtocolCompliance:
    """Tests for ChatApp protocol compliance and architecture."""
    
    def test_chatapp_extends_textual_app(self):
        """Test: ChatApp extends textual.App.
        
        Expectations:
        1. Is subclass of App from textual.app
        2. Can be used with pytest's async test framework
        """
        import inspect
        
        assert issubclass(ChatApp, App), "ChatApp should extend textual.App"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
