"""ChatScreen module - delegates to reactive implementation in screens.py.

This file maintains chat_screen.py name and re-exports ChatScreen from src.ui.screens.
"""

from src.ui.screens import ChatScreen, MessageSent, ChatLogMessage


def compose_message_row(timestamp_display: str, sender: str, message_text: str):
    """Utility to compose a single message row.

    Args:
        timestamp_display: Timestamp as string (formatted)
        sender: Sender name/identifier  
        message_text: Message content
        
    Returns:
        A formatted row suitable for display
    """
    return f"[{timestamp_display}] {sender}: {message_text}"
