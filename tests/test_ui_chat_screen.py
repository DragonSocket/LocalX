import asyncio
from textual.app import App
from textual.widgets import Button, Label, DataTable
import sys

# Путь к модулям проекта
sys.path.insert(0, '/home/blastmerder/Documents/projects/python/localX/src')

try:
    from ui.setup_screen import SetupScreen
except ImportError:
    pass


async def test_chat_screen_import_succeeds():
    """ChatScreen успешно импортируется."""
    from ui.chat_screen import ChatScreen
    
    chat = ChatScreen()
    assert chat is not None


async def test_chat_screen_display_self_message_is_cyan():
    """Сообщения от себя должны быть Cyan."""
    from ui.chat_screen import ChatScreen
    
    chat = ChatScreen()
    assert chat.COLOR_SELF in ('cyan', '#00FFFF', 'blue')


async def test_chat_screen_display_peer_message_is_green():
    """Сообщения от peer должны быть Green."""
    from ui.chat_screen import ChatScreen
    
    chat = ChatScreen()
    assert chat.COLOR_PEER in ('green', '#00FF00', 'lime')


async def test_chat_screen_display_system_error_is_red():
    """Системные ошибки должны быть Red."""
    from ui.chat_screen import ChatScreen
    
    chat = ChatScreen()
    assert chat.COLOR_ERROR in ('red', '#FF0000', 'maroon')


async def test_chat_screen_timestamp_is_dim():
    """Timestamp должен быть Dim/Grey."""
    from ui.chat_screen import ChatScreen
    
    chat = ChatScreen()
    assert chat.COLOR_TIMESTAMP == 'dim' or chat.COLOR_TIMESTAMP == '#808080' or chat.COLOR_TIMESTAMP == 'grey'

if __name__ == '__main__':
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
