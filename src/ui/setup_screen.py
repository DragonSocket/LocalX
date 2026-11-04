"""SetupScreen - Configure connection to a peer."""

from textual.message import Message
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Label, Button


class SetupSubmitted(Message):
    """Message emitted when setup is complete."""


class SetupScreen(App[object]):
    """Setup screen for configuring peer connection."""
    
    CSS = """
    Screen {
        height: 100%;
        width: 80;
        layout: vertical;
        
        .title-label {
            text-align: center;
            color: white;
        }
        
        .host-input, .port-input {
            margin-bottom: 1;
        }
    }

    """

    BINDINGS = [
        Binding(key="q", action="quit"),
        Binding("enter", "connect", description="Connect to peer"),
    ]

    def __init__(
        self, 
        host: str = "127.0.0.1", 
        port: int = 8080
    ):
        super().__init__()
        self.host = host  
        self.port = port
    
    @property
    def config(self) -> dict:
        """Return current configuration."""
        return {
            "host": self.host,
            "port": self.port,
        }

    def compose(self) -> ComposeResult:
        """Compose the SetupScreen layout with inputs and button."""
        from textual.widgets import Label as TextualLabel
        
        yield TextualLabel(f"Host: {self.host}", id="host-display", classes="title-label")
        yield TextualLabel(f"Port: {self.port}", id="port-display", classes="title-label")
        yield Button("Connect", variant="primary", id="connect-btn", classes="connect-button connect-label")

    def handle_setup_submitted(self, event: SetupSubmitted) -> None:
        """Handle SetupSubmitted - this is internal handler pattern."""
        pass

    # Alias for backward compatibility  
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Connect button press - emit SETUP_SUBMITTED message."""
        if event.button.id == "connect-btn":
            self.host = event.data.get("host", self.host) if hasattr(self, 'data') else self.host
            port_data = getattr(event, 'extra', {}).get('port') or self.port
            await self.handle_connect_result(self.host, port_data, success=True)

    def handle_connect_result(self, host: str, port: int, success: bool) -> None:
        """Handle connection result from transport."""
        if not success:
            return
        
        # Simulate successful connection by emitting message
        self.post_message(SetupSubmitted())
    
    def action_quit(self):
        """Quit action handler."""
        self.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    SetupScreen().run()

