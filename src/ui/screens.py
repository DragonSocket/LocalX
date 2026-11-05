"""UI Screens with reactive state attributes and observer patterns.
This module provides reactive state patterns for Textual screens using direct assignment
and property getters/setters, compatible with Textual App pattern.
Reactive observers automatically update UI when state changes occur.
"""


from typing import Optional
from textual.screen import Screen
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Input, Header, Label, RichLog
from textual.message import Message
from textual.notifications import Notification
from src.controller.core import ChatController


class ChatScreen(Screen):
    """ChatScreen with reactive state attributes and observer pattern.
    """

    # Visual identity color names (class attributes)
    COLOR_SELF = 'cyan'       # <blue>My message</blue>
    COLOR_PEER = 'green'      # <green>User: msg</green>
    COLOR_ERROR = 'red'       # Error/System messages  
    COLOR_TIMESTAMP = 'dim'   # Grey/dim timestamps
    

    CSS = '''
    Screen {
        height: 100%;
        width: 100%;
        layout: vertical;
    }

    Header {
        height: 1;
        text-style: bold;
    }

    .scrollable-area {
        overflow-y: auto;
        width: 100%;
    }

    #messages-log {
        width: 100%;
    }

    .input-section {
        height: 5;
        dock: bottom;
        layout: horizontal;
        gap: 1;
    }

    #message-input {
        max-width: flex;
        flex: 1;
    }

    .focused {
        cursor: pointer;
    }

    .disabled-cursor {
        cursor: default;
        text-style: dim;
    }
    '''

    # Keyboard shortcuts
    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
        Binding("ctrl-c", "quit_app", "Quit"),
        Binding("ctrl+n", "new_peer", "New Peer"),
        Binding("ctrl+s", "save_msg", "Save Msg"),
        Binding("esc", "toggle_status", "Status"),
    ]

    def __init__(self, transport=None, storage=None, controller=None):
        """Initialize ChatScreen with reactive state attributes."""
        super().__init__()
        
        self._input_value: str = ""
        self._is_connected: bool = False
        self._peer_ids: set = set()
        self._message_history_count: int = 0
        self._input_ready: bool = True
        self._show_welcome: bool = True
        self._messages_container: Container | None = None
        
        self.transport = transport
        self.storage = storage
        self._controller = controller or None
        
        if self._controller:
            self.state_manager = self._controller.state_manager
        else:
            from src.controller.state import StateManager  
            self.state_manager = StateManager()
            
        self._observers: dict[str, list] = {}

    @property
    def controller(self) -> Optional[ChatController]:
        return self._controller

    @controller.setter
    def controller(self, value: Optional[ChatController]) -> None:
        self._controller = value

    def compose(self) -> ComposeResult:
        """Compose the ChatScreen layout."""
        yield Header(id="header-title")
        with Vertical(id="messages-log", classes="scrollable-area"):
            yield RichLog(id="messages-container", highlight=True, markup=True)
        
        with Horizontal(id="input-section", classes="input-section"):
            yield Input(placeholder="Type a message...", id="message-input")
            yield Button("Send", variant="primary", id="send-btn")

    def action_quit_app(self) -> None:
        self.exit()

    def action_new_peer(self) -> None:
        from textual.widgets import Prompt
        prompt = Prompt("Enter peer address (e.g., peer@localhost:8000):", show_button=True)
        self.mount(prompt, id="peer-prompt")

    def action_save_msg(self) -> None:
        if not self.storage:
            Notification("Storage not available. Skipping save.", severity="warning").post()
            return
        try:
            history = self.storage.fetch_history(limit=100)
            if history:
                Notification(f"Saved {len(history)} messages to storage.", severity="info").post()
            else:
                Notification("No messages to save.", severity="info").post()
        except Exception as e:
            Notification(f"Failed to save messages: {e}", severity="error").post()

    def action_toggle_status(self) -> None:
        if self._is_connected:
            info_text = f"Status: CONNECTED | Peers: {self.peer_count}"
            Notification(info_text, severity="info").post(timeout=5)
            self._show_status_info = not getattr(self, '_show_status_info', True)
        else:
            Notification("Status: DISCONNECTED | Press Ctrl+N for new peer.", severity="info").post(timeout=4)

    @property
    def input_value(self) -> str:
        return self._input_value
    
    @input_value.setter
    def input_value(self, value: str):
        self._previous_input_value = self._input_value
        self._input_value = value.strip() if value else ""
        previous = getattr(self, '_old_input_value', None)
        self.notify_state_change("_input_value", previous, self._input_value)

    @property  
    def is_connected(self) -> bool:
        return self._is_connected
        
    @is_connected.setter  
    def is_connected(self, value: bool):
        if not hasattr(self, '_previous_is_connected') or self._previous_is_connected != self._is_connected:
            self._previous_is_connected = self._is_connected
        self._is_connected = value
        previous = getattr(self, '_old_is_connected_state', None)
        if previous is not None and previous != value:
            self.notify_state_change("_is_connected", previous, value)

    @property
    def peer_count(self) -> int:
        return len(self._peer_ids)

    def notify_state_change(self, attribute: str, old_value, new_value):
        if not hasattr(self, '_observers') or attribute not in self._observers:
            return
        for callback in self._observers[attribute]:
            try:
                callback(attribute, old_value, new_value)
            except Exception as e:
                print(f"[Observer Error] {e}")

    def register_observer(self, attribute: str, callback):
        if not hasattr(self, '_observers'):
            self._observers = {}
        if attribute not in self._observers:
            self._observers[attribute] = []
        self._observers[attribute].append(callback)
        return len(self._observers[attribute])

    def unregister_observer(self, attribute: str, callback):
        if not hasattr(self, '_observers') or attribute not in self._observers:
            return False
        if callback in self._observers[attribute]:
            self._observers[attribute].remove(callback)
            return True
        return False

    @property
    def _previous_input_value(self) -> str | None:
        return getattr(self, '_old_input_value', None)
    
    @_previous_input_value.setter  
    def _previous_input_value(self, value):
        self._old_input_value = value
    
    @property
    def _previous_is_connected(self) -> str | None:
        return getattr(self, '_old_is_connected_state', None)
    
    @_previous_is_connected.setter  
    def _previous_is_connected(self, value):
        self._old_is_connected_state = value

class MessageSent(Message):
    def __init__(self, text: str | None, sender: str | None = "me"):
        super().__init__()
        self.text = text if text is not None else ""
        self.sender = sender or "me"


class ChatLogMessage(Static):
    CSS = '''
    ChatLogMessage {
        padding: 0 2;
    }
    .self-cyan { color: cyan; }
    .peer-green { color: green; }
    .timestamp { text-style: dim; }
    .system-red { color: red; }
    '''

    def __init__(self, text: str, sender: str = None, timestamp=None):
        super().__init__()
        self._text = text
        self._sender = sender or "me"
        self._timestamp = timestamp

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal
        with Horizontal(id="msg-row"):
            yield Static(str(self._timestamp or ""), id="timestamp-display", classes="timestamp")
            yield Static("| ")
            color = "self-cyan" if self._sender.lower() in ["me", "you"] else "peer-green"
            yield Static(f"{self._sender}:", classes=color)
            yield Static(self._text)


class MessageReceived(Message):
    def __init__(self, text: str | None = "", sender: str | None = "peer", timestamp=None):
        super().__init__()
        self.sender = sender or "peer"
        self.text = text if text is not None else ""
        self.timestamp = timestamp
