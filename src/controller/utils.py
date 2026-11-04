"""Message validation utilities for ChatController."""
import re


def validate_message(text: str) -> tuple[bool, str]:
    """
    Validate incoming message text.
    
    Note: type annotation says str but caller may pass None; check both.
    
    Returns:
        (is_valid, error_message) - if valid, error_message is empty string
    
    Raises:
        ValueError: If validation fails with a specific error message.
    """
    # Type check - this must come first before any other checks
    if text is None:
        raise ValueError("Message must be a string")
    
    if not isinstance(text, str):
        raise ValueError("Message must be a string")
    
    # Check for surrogate escapes (invalid unicode) before empty check
    # Surrogate range in Python 3: U+DC00 to U+DFFF
    for s in range(55296, 56320):
        if chr(s) in text:
            raise ValueError("Invalid characters")
    
    # Reject null bytes and control chars except allowed ones (tab/newline/space)
    dangerous_chars = [
        '\x00',   # Null
        '\x0b',   # Vertical tab  
        '\x0c',   # Form feed
    ]
    for char in dangerous_chars:
        if char in text:
            raise ValueError("Invalid characters")
    
    # Reject semicolons with shell commands (command injection)
    if ';' in text:
        dangerous_patterns = ['rm -rf', 'sh ', 'bash ', 'exec ', '> /dev/', '/etc/passwd']
        for pattern in dangerous_patterns:
            if pattern.lower() in text.lower():
                raise ValueError("Invalid characters")
    
    # Empty or whitespace-only check (after type, unicode, control char checks)
    stripped = text.strip()  # standard whitespace includes space, tab, newline etc.
    if not stripped:
        raise ValueError("Message is empty")
    
    # Length limit (100 characters) of actual content
    if len(stripped) > 100:
        raise ValueError("Message too long")
    
    return True, ""
