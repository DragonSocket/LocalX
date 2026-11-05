import pytest
from textual.app import App
from src.ui.chat_app import ChatApp
from src.ui.setup_screen import SetupScreen
from src.ui.screens import ChatScreen

@pytest.mark.asyncio
async def test_setup_to_chat_transition():
    """Test that successfully connecting in SetupScreen transitions to ChatScreen."""
    # We need mocks for transport and storage
    class MockTransport:
        async def stream(self):
            yield "test"
        async def close(self):
            pass

    class MockStorage:
        async def init(self):
                pass
        async def save(self, user, msg):
                pass
        async def fetch_history(self, limit):
                return []
        async def close(self):
                pass

    app = ChatApp(
        host="127.0.0.1",
        port=8080,
        transport=MockTransport(),
        storage=MockStorage()
    )

    async with app.run_test() as pilot:
        print(f"Current screen stack: {app.screen_stack}")
        
        # Perform the transition
        await app.handle_connect_result(host="127.0.0.1", port=8080, success=True)
        
        print(f"Screen stack after transition: {app.screen_stack}")
        assert any(isinstance(screen, ChatScreen) for screen in app.screen_stack)
