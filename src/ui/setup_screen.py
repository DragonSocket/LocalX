"""SetupScreen - Configure connection to a peer."""

from textual.screen import Screen
from textual.message import Message
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Label, Button, Input
from textual.containers import Vertical

class SetupSubmitted(Message):
    """Message emitted when setup is complete."""
    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port


class SetupScreen(Screen):
    """Setup screen for configuring peer connection."""
    
    CSS = """
    Screen {
        height: 100%;
        width: 80;
        layout: vertical;
        padding: 1;
    }
    
    .title-label {
        text-align: center;
        color: white;
        text-style: bold;
    }
    
    .input-group {
        margin-bottom: 1;
        layout: horizontal;
        height: auto;
    }
    
    Label {
        width: 10;
    }
    
    Input {
        width: 1;
    }
    
    #connect-btn {
        margin-top: 1;
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
    
    def compose(self) -> ComposeResult:
        """Compose the SetupScreen layout with inputs and button."""
        yield Label("Configure Connection", classes="title-label")
        
        with Vertical(id="input-container"):
             yield Label("Host:", classes="title-label")
             yield Input(value=self.host, id="host-input")
             
             yield Label("Port:", classes="title-label")
             yield Input(value=str(self.port), id="port-input")
             
        yield Button("Connect", variant="primary", id="connect-btn", classes="connect-button connect-label")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Connect button press."""
        if event.button.id == "connect-btn":
            host_input = self.query_one("#host-input", Input)
            port_input = self.query_one("#port-input", Input)
            
            try:
                host = host_input.value.strip()
                port = int(port_input.value.strip())
                if not host:
                    raise ValueError("Host cannot be empty")
                
                self.post_message(SetupSubmitted(host, port))
            except ValueError as e:
                self.notify(f"Invalid input: {e}", severity="error")

    def action_quit(self):
        """Quit action handler."""
        self.exit()


if __name__ == "__main__":
    SetupScreen().run()

