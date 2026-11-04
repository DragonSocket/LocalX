"""ChatApp - Container for SetupScreen and ChatScreen.

This app orchestrates screen transitions:
1. Starts on SetupScreen (waiting for connection config)
2. On connect success, switches to ChatScreen
3. Handles disconnection by returning to SetupScreen
"""

from typing import Optional, AsyncGenerator
from src.interfaces import Transport, Storage
from textual.app import App, ComposeResult
from textual.widgets import Label
from textual.binding import Binding
import asyncio
from src.ui.setup_screen import SetupScreen
from src.ui.chat_screen import ChatScreen


class ChatApp(App):
    """ChatApp assembles SetupScreen and ChatScreen.

    Architecture:
    - SetupScreen (initial): User configures host/port, clicks "Connect"
    - On success → Pop SetupScreen, Push ChatScreen with transport/storage
    - On disconnect/error → Pop ChatScreen, Push SetupScreen again
    
    Protocol-based DI: Accepts any Transport/Storage implementation.
    
    Lifecycle:
    1. start() → mount(SetupScreen)
    2. handle_connect_result(success=True) → push(ChatScreen)
    3. cleanup_on_exit() → close transport/storage resources
    """

    BINDINGS = [
        Binding(key="q", action="quit_app", description="Quit"),
        Binding(key="c", action="return_to_setup", description="Back to Setup"),
    ]

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        transport=None,
        storage=None,
    ):
        """Initialize ChatApp with optional DI dependencies.

        Args:
            host: Default target host (used in SetupScreen)
            port: Default target port (used in SetupScreen)
            transport: Transport implementation instance (injected)
            storage: Storage implementation instance (injected)
        """
        super().__init__()
        self._initial_host = host
        self._initial_port = port
        self.transport = transport
        self.storage = storage
        self._current_host: str | None = None
        self._current_port: int | None = None

    def compose(self) -> ComposeResult:
        """Compose initial SetupScreen with connection config."""
        yield SetupScreen(
            host=self._initial_host,
            port=self._initial_port,
        )

    def on_mount(self) -> None:
        """Mount lifecycle hook. App starts here."""
        # Initial UI already composed above (SetupScreen)
        pass

    async def handle_connect_result(
        self, host: str, port: int, success: bool
    ) -> None:
        """Handle connection result from SetupScreen submit.

        Args:
            host: Target host address
            port: Target port number
            success: Whether connection succeeded

        Action:
            - success=True → Push ChatScreen (Pop SetupScreen)
            - success=False → Show error on SetupScreen, stay there
        """
        if not success:
            # Connection failed — show error message
            with self:
                from textual.widgets import Static
                yield Static(
                    f"Failed to connect to {host}:{port}.",
                    id="connection-error",
                    classes="error-message",
                )
            return

        # Store connection config
        self._current_host = host
        self._current_port = port

        # If we have transport/storage, create and push ChatScreen
        if self.transport is not None and self.storage is not None:
            chat_screen = ChatScreen(
                transport=self.transport,
                storage=self.storage,
            )
            with self:
                yield chat_screen
        else:
            # If no DI dependencies yet, wait for them to be injected externally
            pass

    def action_quit_app(self) -> None:
        """Quit application (cleanup + exit)."""
        self.cleanup_on_exit()
        self.exit()

    def action_return_to_setup(self) -> None:
        """Return from ChatScreen to SetupScreen."""
        with self:
            yield SetupScreen(
                host=self._current_host or self._initial_host,
                port=self._current_port or self._initial_port,
            )

    async def cleanup_on_exit(self) -> None:
        """Async cleanup before exit.

        Called by action_quit_app, close transport/storage if available.
        """
        if self.transport and hasattr(self.transport, 'close'):
            try:
                if asyncio.iscoroutinefunction(self.transport.close):
                    await self.transport.close()
                else:
                    self.transport.close()
            except Exception as e:
                pass  # Ignore cleanup errors on exit

    async def cleanup_on_close(self) -> None:
        """Custom shutdown logic after close."""
        await self.cleanup_on_exit()

    async def handle_message_received(self, message: str) -> None:
        """Override for handling inbound messages from transport."""
        # For now — stub (future: would notify Controller/Update UI)
        pass

    async def process_stream(self) -> None:
        """Process incoming stream data if available."""
        if not self.transport:
            return

        try:
            async for line in self.transport.stream():
                await self.handle_message_received(line)
        except Exception as e:
            # Stream error — could show notification here
            pass

    def on_key(self, event) -> None:
        """Handle key events at app level (cross-screen)."""
        if event.key.lower() == "q":
            self.action_quit_app()

    async def run_async(self):
        """Override to prepare storage/init on startup."""
        if self.storage:
            await self.storage.init()

    def action_quit(self) -> None:
        """Action: Quit the application."""
        if self.storage:
            asyncio.create_task(self.storage.close())
        self.exit()


class ChatAppTest(App):
    """Test wrapper for ChatApp - simplified for testing."""
    
    BINDINGS = [
        Binding(key="q", action="quit", description="Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Start with a placeholder screen for testing."""
        from textual.widgets import Label
        
        yield Label("ChatApp Test Mode", id="test-label")
    
    def on_mount(self) -> None:
        # Inject ChatApp logic into test wrapper
        if hasattr(self, 'chat_app'):
            self.setup_chatapp_integration()


def create_test_app(
    host: str = "127.0.0.1",
    port: int = 8080,
    transport=None,
    storage=None,
):
    """Factory for test apps.

    Args:
        host: Host address
        port: Port number
        transport: Transport implementation (optional)
        storage: Storage implementation (optional)
    
    Returns:
        Runnable App instance ready for testing
    """
    app = ChatApp(host=host, port=port, transport=transport, storage=storage)
    return app
