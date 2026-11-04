"""Test configuration file for VEGA-CHAT screens.

Per TDD: These tests define expected behavior for Task 7.1 (Text Capture/Management).
"""

import asyncio
import pytest
from textual.app import App, ComposeResult
from textual.message import Message
from textual.widgets import Label, Button, RichLog, Input, Static
from textual.containers import Horizontal


class SetupSubmittedMessage(Message):
    """Custom message for setup completion."""
    pass


# Widget aliases
ChatInput = Input
ChatLog = RichLog


class TestChatScreenApp(App[object]):
    """Minimal ChatScreen app implementing text capture and message management.

    Expected composition:
    - Message input (Input widget with id="message-input") - TEXT CAPTURE
    - Send button (Button with id="send-btn") - EVENT EMITTER
    - Messages log container (RichLog with id="messages-log") - DISPLAY
    
    Text Capture & Management Features:
    - Captures text via Input.text property
    - Validates message length (>100 rejected)
    - Clears input after send via set_text("")
    - Emits MessageSent event on button press/enter key
    """

    CSS = 'Screen {height: 100%; width: 80; layout: vertical}'

    BINDINGS = [("q", "quit", "Quit"), ("ctrl-c", "quit", "Quit")]
    
    POST_MESSAGE_REGISTRY = {}

    def __init__(self):
        super().__init__()
        self._messages_sent_count = 0
        self.POST_MESSAGE_REGISTRY["SETUP_SUBMITTED"] = SetupSubmittedMessage

    @property
    def config(self):
        return {"host": "127.0.0.1", "port": 8080}
    
    def compose(self) -> ComposeResult:
        """Compose the ChatScreen layout."""
        messages_log = RichLog(id="messages-log", classes="log-container")
        input_area = Horizontal(
            Input(placeholder="Type a message...", id="message-input"),
            Button("Send", variant="primary", id="send-btn"),
            classes="input-area",
        )
        yield Label("VEGA-CHAT", id="header-title")
        yield messages_log
        yield input_area

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Send button press - emit MessageSent after text capture.

        Text Capture & Management Flow:
        1. User types in Input widget (text captured via .text property)
        2. Presses Enter or clicks Send button
        3. on_button_pressed validates and processes text
        4. Clears input via set_text("") - TEXT MANAGEMENT
        5. Posts MessageSent event for controller
        
        Args:
            event: Button.Pressed event
            
        """
        if getattr(event.button, 'id', '') != "send-btn":
            return
        
        try:
            input_widget = self.query_one("#message-input", ChatInput)
            text = input_widget.text.strip()
            
            if not text:
                if hasattr(event, 'app') and event.app:
                    event.app.notify("Please type a message", severity="error")
                return
            
            if len(text) > 100:
                if hasattr(event, 'app') and event.app:
                    event.app.notify("Message too long (max 100 chars)", severity="error")
                return
            
            await input_widget.set_text("")
            self._messages_sent_count += 1
            await self.post_message("MessageSent")
                
        except Exception as e:
            if hasattr(event, 'app') and event.app:
                event.app.notify(f"Error sending message: {e}", severity="error")

    async def on_key(self, event):
        """Handle Enter key press in Input widget for text capture/send."""
        if event.key == "enter":
            try:
                input_widget = self.query_one("#message-input", ChatInput)
                text = input_widget.text.strip()
                
                if not text:
                    return
                
                if len(text) > 100:
                    self.notify("Message too long (max 100 chars)", severity="error")
                    return
                
                await input_widget.set_text("")
                self._messages_sent_count += 1
                await self.post_message("MessageSent")
                
            except Exception as e:
                self.notify(f"Error: {e}", severity="error")

    async def post_message(self, message: Message | str) -> None:
        """Post a string or Message to app event bus."""
        if isinstance(message, str):
            msg_class = self.POST_MESSAGE_REGISTRY.get(message)
            if not msg_class:
                return
                
            instance = msg_class()
            asyncio.create_task(super().post_message(instance))
            return
        
        asyncio.create_task(super().post_message(message))

    def handle_setup_submitted(self):
        """Handle SETUP_SUBMITTED - internal handler pattern."""
        pass


@pytest.fixture(scope="session")
def chat_app_fixture():
    """Fixture that creates a ChatScreen app for unit testing.

    Provides text capture, management, and event emission functionality.
    """
    return TestChatScreenApp()


__all__ = ["TestChatScreenApp", "chat_app_fixture", "SetupSubmittedMessage"]
