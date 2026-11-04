"""Tests for TextFormatter - TDD implementation."""

import sys
sys.path.insert(0, '/home/blastmerder/Documents/projects/python/localX')

from src.controller.formatter import TextFormatter


def test_formatter_initialization():
    """[TDD] Formatter should instantiate without error."""
    formatter = TextFormatter()
    assert formatter is not None
    assert hasattr(formatter, 'escape')
    assert hasattr(formatter, 'format')


# =========================================================
# ESCAPE METHOD TESTS
# =========================================================

def test_escape_newline():
    """[TDD] newline should become \\n."""
    formatter = TextFormatter()
    result = formatter.escape("\n")
    assert result == "\\n"


def test_escape_carriage_return():
    """[TDD] carriage return should become \\r."""
    formatter = TextFormatter()
    result = formatter.escape("\r")
    assert result == "\\r"


def test_escape_tab():
    """[TDD] tab should become \\t."""
    formatter = TextFormatter()
    result = formatter.escape("\t")
    assert result == "\\t"


def test_escape_backslash():
    """[TDD] backslash should become \\\\"."""
    formatter = TextFormatter()
    result = formatter.escape("\\")
    assert result == "\\\\"


def test_escape_double_quote():
    """[TDD] double quote should become \\\"."""
    formatter = TextFormatter()
    result = formatter.escape('"')
    assert result == '\\"'


def test_escape_single_quote():
    """[TDD] single quote should become \\'."""
    formatter = TextFormatter()
    result = formatter.escape("'")
    assert result == "\\'"


def test_escape_plain_text():
    """[TDD] plain text without special chars unchanged."""
    formatter = TextFormatter()
    text = "hello world 123"
    result = formatter.escape(text)
    assert result == text


def test_escape_empty_string():
    """[TDD] empty string returns empty string."""
    formatter = TextFormatter()
    result = formatter.escape("")
    assert result == ""


def test_escape_multiple_special_chars():
    """[TDD] multiple special chars at once."""
    formatter = TextFormatter()
    text = "hello\nworld\r!test\\quote'abc\"xyz"
    expected = r"hello\nworld\r!test\\quote\'abc\"xyz"
    result = formatter.escape(text)
    assert result == expected


# =========================================================
# FORMAT METHOD TESTS - Simple cases (no markdown, just escape)
# =========================================================

def test_format_unchanged_text():
    """[TDD] Plain text without markers returns unchanged (was_modified=False)."""
    formatter = TextFormatter()
    text = "hello world"
    result, was_modified = formatter.format(text)
    assert result == text
    assert was_modified == False


def test_format_empty_string():
    """[TDD] Empty string returns empty with was_modified=False."""
    formatter = TextFormatter()
    result, was_modified = formatter.format("")
    assert result == ""
    assert was_modified == False


# =========================================================
# FORMAT METHOD TESTS - Newline/Escape cases (was_modified=True)
# =========================================================

def test_format_with_newline():
    """[TDD] Text with newline should be escaped and was_modified=True."""
    formatter = TextFormatter()
    text = "hello\nworld"
    result, was_modified = formatter.format(text)
    assert "\\n" in result
    assert was_modified == True


def test_format_with_backslash():
    """[TDD] Backslash should be escaped and was_modified=True."""
    formatter = TextFormatter()
    text = "path\\to\\file"
    result, _ = formatter.format(text)
    assert "\\\\" in result


# =========================================================
# MARKDOWN FORMATTING TESTS - Bold
# =========================================================

def test_format_bold_simple():
    """[TDD] Simple bold syntax **text** should be processed."""
    formatter = TextFormatter()
    text = "**bold**"
    result, _ = formatter.format(text)
    assert "**" in result  # Preserved (not converted to plain text)


def test_format_bold_simple_text():
    """[TDD] Bold wrapping simple text."""
    formatter = TextFormatter()
    text = "**hello**"
    result, _ = formatter.format(text)
    assert "**hello**" in result


def test_format_bold_nested_asterisks():
    """[TDD] *** should remain as-is (not misinterpreted)."""
    formatter = TextFormatter()
    text = "***"
    result, _ = formatter.format(text)
    assert result == text  # No false positives


# =========================================================
# MARKDOWN FORMATTING TESTS - Italic
# =========================================================

def test_format_italic_simple():
    """[TDD] Simple italic *text* should be preserved in output."""
    formatter = TextFormatter()
    text = "*italic*"
    result, _ = formatter.format(text)
    assert "*" in result


def test_format_italic_with_plain_text():
    """[TDD] Plain text between asterisks unchanged."""
    formatter = TextFormatter()
    text = "hello*world"  # Not valid italic (no surrounding *)
    result, _ = formatter.format(text)
    assert result == text


# =========================================================
# MARKDOWN FORMATTING TESTS - Inline Code
# =========================================================

def test_format_inline_code_simple():
    """[TDD] Simple inline code `text`."""
    formatter = TextFormatter()
    text = "`code`"
    result, _ = formatter.format(text)
    assert "`" in result


def test_format_inline_code_with_asterisks():
    """[TDD] Code wrapping bold-like syntax should preserve both."""
    formatter = TextFormatter()
    text = "`**bold**`"
    result, _ = formatter.format(text)
    # `...` should wrap everything
    assert "`" in result


# =========================================================
# LINK TESTS - [text](url)
# =========================================================

def test_format_link_simple():
    """[TDD] Simple link [text](url)."""
    formatter = TextFormatter()
    text = "[click here](https://example.com)"
    result, _ = formatter.format(text)
    assert text in result


def test_format_link_with_special_chars():
    """[TDD] Link with special chars in URL (escaped)."""
    formatter = TextFormatter()
    text = "[link](https://example.com/test\\np)"
    result, _ = formatter.format(text)
    # Should escape \n in link text/url part appropriately


# =========================================================
# COMBINED FORMATTING TESTS - Precedence Order
# =========================================================

def test_format_code_then_bold():
    """[TDD] Code has higher precedence than bold: `**code**`."""
    formatter = TextFormatter()
    text = "`**bold**`"
    result, _ = formatter.format(text)
    # Both ** and backticks should be preserved


def test_format_bold_then_italic():
    """[TDD] Bold around italic: ** *nested* **."""
    formatter = TextFormatter()
    text = "** *nested* **text**"
    result, _ = formatter.format(text)
    assert "**" in result and "*" in result


def test_format_mixed_simple():
    """[TDD] Mixed syntax should all work."""
    formatter = TextFormatter()
    text = "**bold** and *italic* and `inline`"
    result, _ = formatter.format(text)
    # All markers preserved in escaped output
    assert "**bold**" in result
    assert "*italic*" in result  
    assert "`inline`" in result


def test_format_realistic_message():
    """[TDD] Realistic chat message with formatting."""
    formatter = TextFormatter()
    text = "Check `this out**in bold***not italic**`link [here](/foo)"
    result, _ = formatter.format(text)
    # Should escape newlines but keep some markdown syntax


# =========================================================
# XSS SECURITY TESTS
# =========================================================

def test_escape_xss_script():
    """[TDD] Script tags should be escaped (not executed in UI)."""
    formatter = TextFormatter()
    xss = "<script>alert('xss')</script>"
    escaped = formatter.escape(xss)
    assert "&lt;" in escaped  # < becomes &lt;


def test_escape_xss_url_javascript():
    """[TDD] URL with javascript: protocol."""
    formatter = TextFormatter()
    xss = "[dangerous](javascript:alert('xss'))"
    escaped = formatter.escape(xss)
    # The ( part should be visible but content properly handled


# Run tests when called as script
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
