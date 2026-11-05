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
    - On success → Push ChatScreen with transport/storage
    - On disconnect/error → Push SetupScreen again
    
    Protocol-based DI: Accepts any Transport/Storage implementation.
    
    Lifecycle:
    1. start() → on_mount(push SetupScreen)
    2. handle_connect_result(success=True) → push(ChatScreen)
    3. cleanup_on_exit() → close transport/storage resources
    """

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit"),
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
        """Compose empty app container."""
        yield from []

    def on_mount(self) -> None:
        """When app mounts, push the initial SetupScreen."""
        self.push_screen(
            SetupScreen(
                host=self._initial_host,
                port=self._initial_port,
            )
        )

    async def handle_connect_result(
        self, host: str, port: int, success: bool
    ) -> None:
        """Handle connection result from SetupScreen submit.

        Args:
            host: Target host address
            port: Target port number
            success: Whether connection succeeded

        Action:
            - success=True → Push ChatScreen
            - success=False → Show error on SetupScreen, stay there
        """
        if not success:
            # Connection failed — show error message
            # Note: In a real app, we might post a notification or message to SetupScreen
            self.notify(f"Failed to connect to {host}:{port}.", severity="error")
            return

        # Store connection config
        self._current_host = host
        self._current_port = port

        # If we have transport/storage, create and push ChatScreen
        if self.transport and self.storage:
            chat_screen = ChatScreen(
                transport=self.transport,
                storage=self.storage,
            )
            self.push_screen(chat_screen)
        else:
            # If no DI dependencies yet, wait for them to be injected externally
            self.notify("Transport or Storage not configured!", severity="error")

    def action_return_to_setup(self) -> None:
        """Return from ChatScreen to SetupScreen."""
        self.push_screen(
            SetupScreen(
                host=self._current_host or self._initial_host,
                port=self._current_port or self._initial_port,
            )
        )

    @property
    def config(self) -> dict[str, str | int]:
        """Return current configuration."""
        return {
            "host": self._current_host or self._initial_host,
            "port": self._current_port or self._initial_port,
        }

    async def cleanup_on_exit(self) -> None:
        """Async cleanup before exit."""
        if self.transport:
            await self.transport.close()
        
        if self.storage:
            await self.storage.close()

    async def handle_message_received(self, message: str) -> None:
        """Override for handling inbound messages from transport."""
        # For now — stub (future: would notify Controller/Update UI)
        pass

    async def process_stream(self) -> None:
        """Process stream data from transport."""
        if not self.transport:
            return
        
        try:
            async for line in self.transport.stream():
                await self.handle_message_received(line)
        except Exception:
            # Stream error — could show notification here
            pass

    def on_key(self, event) -> None:
        """Handle key events across screens."""
        if event.key.lower() == "q":
            self.action_quit()

    async def run_async(self, *args, **kwargs) -> None:
        """Override to prepare storage/init on startup."""
        if self.storage:
            await self.storage.init()
        await super().run_async(*args, **kwargs)

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
