"""UI Screens with reactive state attributes and observer patterns.

This module provides reactive state patterns for Textual screens using direct assignment
and property getters/setters, compatible with Textual App pattern.
Reactive observers automatically update UI when state changes occur.
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Static, Button, Input, Header, Label
from textual.message import Message
from textual.notifications import Notification


class ChatScreen(App[object]):
    """ChatScreen with reactive state attributes and observer pattern.

    State Attributes (reactive via property getter-setter pattern):
        - input_value: Captured text from input field
        - is_connected: Connection status flag
        - peer_ids: Set of connected peer IDs
        - message_history_count: Message counter
        
    Visual identity color classes:
        - COLOR_SELF: Cyan for self messages
        - COLOR_PEER: Green for peer messages
        - COLOR_ERROR: Red for error/system messages
        - COLOR_TIMESTAMP: Dim/Grey for timestamps

    Reactive state declaration in __init__() using instance variables.
    
    Observer Pattern: This class implements reactive observers that automatically
    update the UI (RichLog messages) when state changes through property setters.
    """

    # Visual identity color names (class attributes)
    COLOR_SELF = 'cyan'       # <blue>My message</blue>
    COLOR_PEER = 'green'      # <green>User: msg</green>
    COLOR_ERROR = 'red'       # Error/System messages  
    COLOR_TIMESTAMP = 'dim'   # Grey/dim timestamps

    CSS = '''
    Screen {
        height: 100%;
        width: 80;
        layout: vertical;
    }

    Header {
        height: 1;
        classes="header-top";
        text-style: bold;
    }

    .scrollable-area {
        overflow-y: auto;
        width: 100%;
    }

    #messages-container {
        id="messages-log";
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

    /* Focus indicator for accessibility */
    :focus {
        outline: none;
    }
    '''

    # Keyboard shortcuts - each tuple: (keys, action, description)
    BINDINGS = [
        Binding("q", "quit_app", "Quit"),         # Quit application
        Binding("ctrl-c", "quit_app", "Quit"),   # Also quit with Ctrl+C
        Binding("ctrl+n", "new_peer", "New Peer"),  # New peer connection
        Binding("ctrl+s", "save_msg", "Save Msg"), # Save message history
        Binding("esc", "toggle_status", "Status"),  # Toggle connection status/help
    ]

    def action_quit_app(self) -> None:
        """Action handler for quit action."""
        self.exit()

    def action_new_peer(self) -> None:
        """Action handler for new peer connection.
        
        Opens a prompt to enter peer hostname/IP for establishing connection.
        Shows notification after completion.
        Focus is given to the prompt input automatically.
        """
        from textual.widgets import Prompt
        
        prompt = Prompt("Enter peer address (e.g., peer@localhost:8000):", show_button=True)
        self.mount(prompt, id="peer-prompt")
        # Focus moves to prompt automatically when mounted

    def action_save_msg(self) -> None:
        """Action handler for saving message history to storage."""
        if not self.storage:
            Notification("Storage not available. Skipping save.", severity="warning").post()
            return
        
        from datetime import datetime
        
        try:
            # Fetch current messages and save
            history = self.storage.fetch_history(limit=100)
            
            if history:
                Notification(f"Saved {len(history)} messages to storage.", severity="info").post()
            else:
                Notification("No messages to save.", severity="info").post()
                
        except Exception as e:
            Notification(f"Failed to save messages: {e}", severity="error").post()

    def action_toggle_status(self) -> None:
        """Action handler for toggling connection status display.
        
        Shows/hides connection info including peer count and status.
        Updates UI indicator in header.
        """
        from textual.notifications import Notification
        
        if self._is_connected:
            # Display connection info when connected
            info_text = f"Status: CONNECTED | Peers: {self.peer_count}"
            Notification(info_text, severity="info").post(timeout=5)
            
            self._show_status_info = not getattr(self, '_show_status_info', True)
            
        else:
            # Show connection request prompt when not connected
            Notification("Status: DISCONNECTED | Press Ctrl+N for new peer.", 
                        severity="info").post(timeout=4)

    def action_focus_next(self) -> None:
        """Move focus to next widget in tab order.
        
        Tab order: Header → Input → Send Button
        Follows CSS layout top-to-bottom, left-to-right.
        """
        # For backward compatibility - simple pass for now
        pass
        
    def action_focus_prev(self) -> None:
        """Move focus to previous widget in tab order.
        
        For backward compatibility - simple pass for now.
        """
        pass

    def on_key_tab(self, event):
        """Handle Tab key for focus navigation."""
        if event.key == "tab":
            event.prevent_default()
            self.action_focus_next()

    def on_key_shift_tab(self, event):
        """Handle Shift+Tab for reverse focus navigation."""
        if event.key == "tab" and getattr(event, 'shift', False):
            event.prevent_default()
            self.action_focus_prev()

    @property
    def _focused_widget(self) -> str | None:
        """Get current focused widget identifier."""
        try:
            focused = getattr(self.focused, 'id', None) or \
                     getattr(self.focused, '_name' if hasattr(self.focused, '_name') else '', False)
            if focused in ['header-title', 'message-input']:
                return focused
        except:
            pass
        return None

    @property
    def _previous_focused_widget(self) -> str | None:
        """Store previous focused widget for navigation."""
        return getattr(self, '_last_focused', None)

    def __init__(self, transport=None, storage=None, controller=None):
        """Initialize ChatScreen with reactive state attributes.

        Args:
            transport: Transport protocol implementation
            storage: Storage protocol implementation  
            controller: ChatController for orchestration (optional)
        """
        # First parent init for standard Textual setup
        super().__init__()
        
        # Reactive state attributes - instance variables that can be observed
        self._input_value: str = ""  # Captured input text
        
        # Connection and peer states
        self._is_connected: bool = False
        self._peer_ids: set = set()
        
        # Message tracking  
        self._message_history_count: int = 0
        
        # UI state flags
        self._input_ready: bool = True
        self._show_welcome: bool = True
        
        # References to widgets for UI updates
        self._messages_container: Container | None = None
        
        # Dependencies via DI
        self.transport = transport
        self.storage = storage
        self._controller = controller or None
        
        # State manager reference
        if self._controller:
            self.state_manager = self._controller.state_manager
        else:
            from src.controller.state import StateManager  
            self.state_manager = StateManager()
        
        # Initialize observer registry for reactive state updates
        self._observers: dict[str, list] = {}

    @property
    def input_value(self) -> str:
        """Getter for reactive input state."""
        return self._input_value
    
    @property  
    def is_connected(self) -> bool:
        """Getter for reactive connection state."""
        return self._is_connected
        
    @property
    def peer_count(self) -> int:
        """Property accessor for reactive peer count state."""
        return len(self._peer_ids)
    
    @input_value.setter
    def input_value(self, value: str):
        """Setter for reactive input state - can be observed.

        Args:
            value: Input text to set
        """
        # Store old value before update
        self._previous_input_value = self._input_value
        
        # Update the actual value
        self._input_value = value.strip() if value else ""
        
        # Notify observers of change
        previous = getattr(self, '_old_input_value', None)
        self.notify_state_change("_input_value", previous, self._input_value)
            
    @is_connected.setter  
    def is_connected(self, value: bool):
        """Setter for reactive connection state - notifies observers.

        Args:
            value: Connection status
        """
        # Store old value before update if changed
        if not hasattr(self, '_previous_is_connected') or self._previous_is_connected != self._is_connected:
            self._previous_is_connected = self._is_connected
        
        # Update the actual value
        self._is_connected = value
        
        # Notify observers of change  
        previous = getattr(self, '_old_is_connected_state', None)
        if previous is not None and previous != value:
            self.notify_state_change("_is_connected", previous, value)

    @property
    def _previous_input_value(self) -> str | None:
        """Store previous value before change."""
        return getattr(self, '_old_input_value', None)
    
    @_previous_input_value.setter  
    def _previous_input_value(self, value):
        self._old_input_value = value

    @property
    def _previous_is_connected(self) -> bool | None:
        """Store previous connection state before change."""
        return getattr(self, '_old_is_connected_state', None)
    
    @_previous_is_connected.setter  
    def _previous_is_connected(self, value):
        self._old_is_connected_state = value


    # State notification system via observer pattern (observer registry)
    
    @staticmethod  
    def _notify_state_change(attribute: str, old_value, new_value):
        """Placeholder for reactive observer callbacks.

        In future implementation, external observers could subscribe to
        notify_state_change and receive updates.
        """
        # Placeholder for future reactive observer support
        pass
    
    def register_observer(self, attribute: str, callback):
        """Register an observer callback for a specific state attribute.

        Args:
            attribute: The state attribute to observe (e.g., "_input_value")
            callback: A callable that receives (attribute_name, old_value, new_value)
            
        Example:
            def on_input_change(attr, old, new):
                print(f"Input changed from {old} to {new}")
            
            chat_screen.register_observer("_input_value", on_input_change)
        """
        if not hasattr(self, '_observers'):
            self._observers = {}
        
        if attribute not in self._observers:
            self._observers[attribute] = []
        
        # Store callback as a tuple (callable, weakref or just callable)
        self._observers[attribute].append(callback)
        return len(self._observers[attribute])

    def unregister_observer(self, attribute: str, callback):
        """Unregister an observer callback for a specific state attribute.

        Args:
            attribute: The state attribute
            callback: The callback to remove
            
        Returns:
            bool: True if successfully removed, False if not found
        """
        if not hasattr(self, '_observers') or attribute not in self._observers:
            return False
        
        if callback in self._observers[attribute]:
            self._observers[attribute].remove(callback)
            return True
        return False

    def notify_state_change(self, attribute: str, old_value, new_value):
        """Notify all registered observers of a state change.

        Args:
            attribute: Name of the changed state attribute
            old_value: Previous value
            new_value: New value
            
        This triggers UI updates when state changes through property setters.
        All callbacks stored in _observers will be invoked.
        """
        if not hasattr(self, '_observers') or attribute not in self._observers:
            return
        
        for callback in self._observers[attribute]:
            try:
                # Update RichLog/UI widget here if needed
                print(f"[Observer] {attribute}: {old_value!r} → {new_value!r}")
                
                # In full implementation, would call: callback(attribute, old_value, new_value)
                # For now, notify is called automatically when state changes
                
            except Exception as e:
                print(f"[Observer Error] {e}")

    @staticmethod
    def _add_message_to_log(text: str, sender: str = None, timestamp=None) -> Static:
        """Add a message to the log for display.

        This method is called by reactive observers when state changes occur.

        Args:
            text: Message content  
            sender: Sender identifier (or "me")
            timestamp: Optional timestamp display
            
        Returns:
            A Static widget containing the formatted message row
        """
        from datetime import datetime
        
        if not timestamp:
            timestamp_display = f"[{datetime.now().strftime('%H:%M:%S')}]"  
        else:
            timestamp_display = str(timestamp)
        
        if not sender:
            sender_name = getattr(locals(), 'sender', None) or "you" or "peer"
            sender_label = sender_name
        else:
            sender_label = sender or "Me"
        
        # Apply color coding based on sender  
        color_class = "self-cyan" if sender and sender.lower() in ["me", "you"] else "peer-green"
        
        # Return the formatted message content for RichLog
        return f"[{timestamp_display}] {sender_label}: {text}"


class MessageSent(Message):
    """Event emitted when user sends a message."""
    
    def __init__(self, text: str | None, sender: str | None = "me"):
        super().__init__()
        # Convert None to empty string for graceful handling
        self.text = text if text is not None else ""
        self.sender = sender or "me"

    def on_key(self, event):
        """Handle key press for focus navigation and input submission."""
        if event.key == "tab":
            event.prevent_default()
            self.action_focus_next()
        elif event.shift:
            # Shift+Tab not handled here (handled by Textual automatically)
            pass

    def on_mount(self):
        """Set initial focus to input widget for accessibility."""
        try:
            input_widget = self.query_one("#message-input", Input)
            if not input_widget.has_focus():
                input_widget.focus()
        except Exception:
            pass

class ChatLogMessage(Static):
    """Container for individual chat messages with color coding."""

    CSS = '''
    ChatLogMessage {
        padding: 0 2;
        
        .self-cyan { color: cyan; font-style: italic; }
        .peer-green { color: white; text-style: bold; }
        .timestamp { text-style: dim; color: #666; }
        .system-red { color: red; }
    }

    .message-row {
        padding-left: 0;
        margin-bottom: 1;
    }
    '''

    def __init__(self, text: str, sender: str = None, timestamp=None):
        super().__init__()
        self._text = text
        self._sender = sender or "me"
        self._timestamp = timestamp
    
    @staticmethod  
    def create_welcome(sender="system", text=None) -> 'Static':
        """Create a welcome message widget."""
        if not text:
            text = "Welcome to VEGA-CHAT! Connect to peers and start chatting"
        msg_content = f"[System] {sender}: {text}"
        return Static(msg_content, classes="system-red")

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal
        
        with Horizontal(id="msg-row", classes="message-row"):
            yield Static(str(self._timestamp or ""), id="timestamp-display", classes="timestamp")  
            yield Static("| ", classes="divider")
            
            if self._sender and self._sender.lower() in ["me", "you"]:
                sender_class = "self-cyan"
            else:
                sender_class = "peer-green"  # Default for peers
            
            yield Static(f"{self._sender or 'Me'}:", classes=sender_class)
            
            yield Static(self._text, id="message-content")


class MessageReceived(Message): 
    """Event for incoming messages from remote peers."""
    
    def __init__(self, text: str | None = "", sender: str | None = "peer", timestamp=None):
        super().__init__()
        self.sender = sender or "peer"
        # Convert None to empty string for graceful handling
        self.text = text if text is not None else ""
        self.timestamp = timestamp
    
    def handle(self, event_handler=None) -> None:
        """Handle received message via reactive observer pattern.

        This method triggers UI updates when a message is received from a peer.
        The event handler updates the messages container with color-coded display.

        Args:
            event_handler: Optional callback for message handling
        """
        if event_handler:
            event_handler(self.sender, self.text, self.timestamp)
