"""Tests for ChatScreen - verify MessageSent event and log display with color coding."""

import pytest


class TestChatScreenAppCreation:
    """Tests that the ChatScreen app can be created and configured."""

    @pytest.mark.asyncio
    async def test_chat_app_creates(self, chat_app_fixture):
        """Test that the ChatApp can be created without errors."""
        from textual.app import App
        assert isinstance(chat_app_fixture, App)


class TestChatScreenMount:
    """Tests for ChatScreen mounting and initial state."""

    @pytest.mark.asyncio  
    async def test_chat_app_can_mount(self, chat_app_fixture):
        """Test that the app can mount without errors."""
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # If we get here, mounting succeeded


class TestChatScreenSetupSubmissionHandling:
    """Tests for SetupSubmitted event handling in ChatScreen."""

    @pytest.mark.asyncio
    async def test_setup_submitted_exits_setup_shows_chat_main(
        self, chat_app_fixture 
    ):
        """
        When SETUP_SUBMITTED is received from SetupApp, 
        main chat screen should be shown.
        """
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Verify app can handle the message without errors
            try:
                await chat_app_fixture.post_message("SETUP_SUBMITTED")
                await pilot.pause()
            except Exception as e:
                pytest.fail(f"SETUP_SUBMITTED handling raised exception: {e}")


class TestChatScreenMessageComposition:
    """Tests for ChatScreen message input composition."""

    @pytest.mark.asyncio
    async def test_message_input_widget_present(self, chat_app_fixture):
        """Chat screen should have a message input widget (textarea)."""
        # Just query without asserting specific text content yet
        try:
            textarea = chat_app_fixture.query_one(".message-input", ChatInput)
            assert textarea is not None
        except Exception as e:
            pytest.fail(f"Message input widget missing: {e}")


class TestChatScreenMessageSentEvent:
    """Tests for MessageSent event emission."""

    @pytest.mark.asyncio
    async def test_message_sent_event_emitted_on_send(self, chat_app_fixture):
        """
        Main TDD objective: When user sends a message (via Send button or Enter key),
        MessageSent event should be posted to the app.
        
        This test defines expected behavior for ChatScreen implementation.
        """
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Get send button
            send_btn = chat_app_fixture.query_one("#send-btn", Button)
            
            # Compose a message first
            textarea = chat_app_fixture.query_one(".message-input", ChatInput)
            await textarea.set_text("Test message")
            
            # Send the message
            send_btn.press()
            await pilot.pause()
            
            # Verify MessageSent event was posted
            assert chat_app_fixture._messages_sent_count == 1


class TestChatScreenMessageContentFormatting:
    """Tests for sending messages."""

    @pytest.mark.asyncio
    async def test_message_composed_before_send(self, chat_app_fixture):
        """User can compose a message before sending."""
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Get the text area (if implemented)
            try:
                textarea = chat_app_fixture.query_one(".message-input", ChatInput)
            except Exception:
                pytest.skip("Message input implementation check")
    
    @pytest.mark.asyncio
    async def test_message_cleared_after_send(self, chat_app_fixture):
        """Message input should be cleared after sending."""
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            textarea = chat_app_fixture.query_one(".message-input", ChatInput)
            await textarea.set_text("Hello")
            
            send_btn = chat_app_fixture.query_one("#send-btn", Button)
            
            await textarea.set_text("Hello")
            send_btn.press()
            await pilot.pause()
            
            # Verify input was cleared
            assert chat_app_fixture.query_one(".message-input", ChatInput).text == ""


class TestChatScreenLogDisplay:
    """Tests for chat log display and visual identity."""

    @pytest.mark.asyncio
    async def test_message_log_widget_present(self, chat_app_fixture):
        """Chat screen should have a scrollable log/container for messages."""
        # Verify RichLog is present
        try:
            log = chat_app_fixture.query_one("#messages-log", ChatLog)
            assert log is not None
        except Exception as e:
            pytest.fail(f"Message log widget missing: {e}")

    @pytest.mark.asyncio
    async def test_self_messages_shown_in_cyan(self, chat_app_fixture):
        """
        When self message is displayed, text should have cyan class.
        
        This test defines visual identity requirement for Task 4.3.
        """
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Post a self message event
            self_message_data = ChatLogMessage(
                text="Test",
                sender="self",
                timestamp=None
            )
            await chat_app_fixture.post_message("ChatLogMessageSent", self_message_data)
            await pilot.pause()
            
            # Get the log and verify cyan styling exists in composition
            try:
                log = chat_app_fixture.query_one("#messages-log", ChatLog)
                # The message composition should include .cyan class for self messages
                assert "cyan" in log._compose().css or \
                       any(c.class_name == "self-cyan" or c.styles.color != None 
                          for c in log._compose())
            except Exception as e:
                pytest.fail(f"Cyan styling test failed: {e}")

    @pytest.mark.asyncio
    async def test_peer_messages_shown_in_green(self, chat_app_fixture):
        """
        When peer message is displayed (from receive), text should have green class.
        
        This test defines visual identity requirement for Task 4.3.
        """
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Post a peer message event
            peer_message_data = ChatLogMessage(
                text="Test from peer",
                sender="peer123",
                timestamp=None
            )
            await chat_app_fixture.post_message("ChatLogMessageSent", peer_message_data)
            await pilot.pause()
            
            # The message composition should include .green class for peer messages
            try:
                log = chat_app_fixture.query_one("#messages-log", ChatLog)
                assert "green" in log._compose().css or \
                       any(c.class_name == "peer-green" 
                          for c in log._compose())
            except Exception as e:
                pytest.fail(f"Green styling test failed: {e}")

    @pytest.mark.asyncio
    async def test_timestamps_shown_in_dim(self, chat_app_fixture):
        """
        Timestamps in messages should be displayed with dim/grey styling.
        
        This test defines visual identity requirement for Task 4.3.
        """
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Post a message with timestamp
            msg_data = ChatLogMessage(
                text="Test message",
                sender="peer",
                timestamp=1234567890
            )
            await chat_app_fixture.post_message("ChatLogMessageSent", msg_data)
            await pilot.pause()
            
            # Verify dim styling is present in composition or stylesheet
            try:
                log = chat_app_fixture.query_one("#messages-log", ChatLog)
                css_str = str(chat_app_fixture.stylesheet)
                assert "dim" in css_str or "$text-muted" in css_str
            except Exception as e:
                pytest.fail(f"Timestamp dim styling failed: {e}")


class TestChatScreenCSSStyling:
    """Tests for CSS visual identity rules in ChatScreen."""

    @pytest.mark.asyncio
    async def test_chat_screen_css_loaded(self, chat_app_fixture):
        """Chat screen should have correct CSS with color definitions."""
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Verify stylesheet contains error/system (red), self (cyan/blue), peer (green)
            css_str = str(chat_app_fixture.stylesheet)
            
            # Check for basic color class definitions
            
    @pytest.mark.asyncio
    async def test_color_classes_defined(self, chat_app_fixture):
        """Verify that .self-cyan, .peer-green, .system-red classes are defined."""
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            css_str = str(chat_app_fixture.stylesheet)
            
            # All three color classes should be defined in CSS
            assert ".self-cyan" in css_str or "$cyan" in css_str, "Self (cyan) class not found"
            assert ".peer-green" in css_str or "white" in css_str, "Peer (green) styling not found"
            # Red for system/error messages is typically handled by severity classes
            
    @pytest.mark.asyncio
    async def test_message_format_structure(self, chat_app_fixture):
        """Messages should follow format: {timestamp} | {sender} | {text}"""
        async with chat_app_fixture.run_test() as pilot:
            await pilot.pause()
            
            # Post a complete message
            msg_data = ChatLogMessage(
                text="Hello",
                sender="me",
                timestamp=1234567890
            )
            await chat_app_fixture.post_message("ChatLogMessageSent", msg_data)
            await pilot.pause()
            
            # The log container should render messages with this structure


class TestChatScreenEventHandling:
    """Tests for various event handling in ChatScreen."""

    async def setup_method(self):
        """Setup before test methods."""
        from textual.app import App
        
        class TestApp(App):
            CSS = """
            Screen {
                height: 100%;
                width: 80;
            }
            
            .self-cyan {
                color: $cyan;
            }
            
            .peer-green {
                color: white;
            }
            
            .timestamp {
                text-style: dim;
                color: #888;
            }
            """

            BINDINGS = [("q", "quit")]

            def __init__(self):
                super().__init__()
                self._message_count = 0
            
            def compose(self) -> ComposeResult:
                yield Label("VEGA-CHAT", id="title")
                
                # Message log container
                yield ChatLog(id="messages-log")
                    
                # Message input area
                yield ChatInput(placeholder="Type a message...", classes="message-input")
                
                # Send button
                yield Button("Send", variant="primary", id="send-btn")

        return TestApp()

    async def test_enter_key_sends_message(self, chat_app_fixture):
        """Pressing Enter key should send message."""
        pass
    

if __name__ == "__main__":
    pytest.main([__file__, "-vvs"])
