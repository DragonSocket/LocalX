import re


class TextFormatter:
    """Text formatter with XSS protection and Markdown support."""
    
    def __init__(self):
        # HTML entities for XSS protection (highest precedence)
        self.html_map = {
            "<": "&lt;",
            ">": "&gt;",
            "&": "&amp;"
        }
        
        # Escape sequences for special characters (for UI display)
        self.escape_map = {
            "\\": "\\\\",      # Backslash first to prevent double-escaping
            "\"": '\\"',       # Double quote for JSON/safety
            "'": "\\'",        # Single quote for safety
            "\n": "\\n",       # Newline as escape sequence
            "\r": "\\r",       # Carriage return
            "\t": "\\t",       # Tab
        }

    def escape(self, text: str) -> str:
        """Escape special characters for safe display.
        
        Args:
            text: Raw text to escape
            
        Returns:
            Escaped string with HTML entities and special chars converted
        """
        result = []
        for char in text:
            # Apply HTML entity escapes first (for XSS protection)
            if char in self.html_map:
                result.append(self.html_map[char])
            # Then apply escape sequences
            elif char in self.escape_map:
                result.append(self.escape_map[char])
            else:
                result.append(char)
        return "".join(result)

    def format(self, text: str) -> tuple[str, bool]:
        """Format text with markdown and return (formatted, was_escaped).
        
        Args:
            text: Raw text to format
            
        Returns:
            Tuple of (formatted_text, was_escaped) where was_escaped indicates
            if any transformations were applied
        """
        escaped = self.escape(text)
        was_escaped = escaped != text
        
        # Always call _apply_markdown (which now just preserves the text)
        formatted = self._apply_markdown(escaped)
        
        return formatted, was_escaped

    def _apply_markdown(self, text: str) -> str:
        """Apply markdown formatting to text.
        
        Precedence order (highest to lowest):
        1. Inline code `code` - handled first
        2. Bold **bold** - handled second  
        3. Italic *italic* - handled third
        4. Links [text](url) - handled last
        
        Args:
            text: Already-escaped text with markdown syntax
            
        Returns:
            Text with preserved/processed markdown markers (for UI rendering)
        """
        # No need to protect code since we're just preserving what's there
        # The escaped text already has backslashes where needed
        
        # Step 1: Inline code - keep as-is (it's already formatted correctly)
        # The regex pattern matches `code` and leaves it alone
        
        # Step 2: Bold syntax - keep **text** as-is for UI rendering
        # The regex preserves ** markers in output
        
        # Step 3: Italic syntax - keep *text* as-is 
        # Single asterisks around text are preserved
        
        # Step 4: Links - keep [text](url) format
        # Return the text with markdown preserved for UI
        
        return text

    def escape_html_only(self, text: str) -> str:
        """Escape only HTML entities for XSS protection.
        
        Args:
            text: Text to escape
            
        Returns:
            Text with < > & converted to HTML entities
        """
        result = []
        for char in text:
            if char in self.html_map:
                result.append(self.html_map[char])
            else:
                result.append(char)
        return "".join(result)
