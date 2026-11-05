import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.main import VEGAChatApp
from src.ui.setup_screen import SetupScreen
from src.ui.chat_screen import ChatScreen
from src.interfaces import Transport, Storage

@pytest.mark.asyncio
async def test_setup_to_chat_transition():
    """
    E2E Test: Verify that after providing configuration on SetupScreen 
    and clicking 'Connect', the app transitions to ChatScreen.
    """
    # 1. Setup mocks
    mock_storage = MagicMock(spec=Storage)
    mock_storage.init = AsyncMock()
    mock_storage.close = AsyncMock()
    mock_storage.save = AsyncMock(return_value=True)
    mock_storage.fetch_history = AsyncMock(return_value=[])

    mock_transport = MagicMock(spec=Transport)
    mock_transport.send = AsyncMock(return_value=True)
    mock_transport.stream = AsyncMock(return_value=[])
    mock_transport.close = AsyncMock()

    # 2. Initialize App
    app = VEGAChatApp(storage=mock_storage)

    # 3. Patch NcatTransport in src.main so it returns our mock
    with patch("src.main.NcatTransport", return_value=mock_transport):
        async with app.run_test() as pilot:
            # 4. Verify we start at SetupScreen
            assert isinstance(app.screen, SetupScreen), \
                f"Expected SetupScreen, got {type(app.screen).__name__}"

            # 5. Interact with SetupScreen
            await pilot.type_text("#host-input", "127.0.0.1")
            await pilot.type_text("#port-input", "9000")
            
            # Click the connect button
            await pilot.click("#connect-btn")

            # 6. Wait for transition to ChatScreen
            # We need to yield to let the message be processed and the screen switched
            
            # Try to wait for the screen to change
            found_chat_screen = False
            for _ in range(20):
                if isinstance(app.screen, ChatScreen):
                    found_chat_screen = True
                    break
                await asyncio.sleep(0.05)

            assert found_chat_screen, \
                f"Expected transition to ChatScreen, but still on {type(app.screen).__name__}"
            
            # 7. Verify the injected dependencies in ChatScreen
            chat_screen = app.screen
            assert isinstance(chat_screen, ChatScreen)
            
            # Check if the controller is correctly wired
            assert chat_screen.controller is not None
            assert chat_screen.transport == mock_transport
            assert chat_screen.storage == mock_storage
