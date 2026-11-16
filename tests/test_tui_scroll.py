"""Regression tests for transcript scrolling: max offset and buffer-trim fix."""

from src.ui.tui import ChatTUI, MAX_BUFFER_LINES, STYLE_ME


def make_tui(rows: int = 10, cols: int = 20) -> ChatTUI:
    tui = ChatTUI()
    tui._terminal_size = lambda: (rows, cols)
    return tui


def fill(tui: ChatTUI, n: int) -> None:
    for i in range(n):
        tui._buffer.append((STYLE_ME, f"line-{i}"))


def test_max_scroll_shows_full_screen_of_old_lines() -> None:
    """Ctrl+Home must land on a full page, not a single line."""
    tui = make_tui(rows=10, cols=20)
    fill(tui, 50)
    assert tui._max_scroll() == 50 - 10
    tui._scroll = tui._max_scroll()
    rendered = list(tui._render_transcript())
    assert len(rendered) == 10
    assert "line-0" in "".join(text for _, text in rendered)


def test_max_scroll_zero_when_buffer_shorter_than_screen() -> None:
    tui = make_tui(rows=10, cols=20)
    fill(tui, 5)
    assert tui._max_scroll() == 0


def test_scroll_corrected_when_buffer_trims_from_top() -> None:
    """Dropping old lines must shift the manual offset, not blank the view."""
    tui = make_tui(rows=10, cols=20)
    for i in range(MAX_BUFFER_LINES):
        tui._buffer.append((STYLE_ME, f"old-{i}"))

    tui._scroll = 80
    tui.add_message(STYLE_ME, "new-msg")
    # One line was removed from the top -> offset shrinks by exactly one.
    assert tui._scroll == 79
    assert tui._unread == 1

    # Extreme case: offset larger than the buffer must clamp to a valid view.
    tui._scroll = MAX_BUFFER_LINES + 100
    for _ in range(5):
        tui.add_message(STYLE_ME, "extra")
    assert tui._scroll == MAX_BUFFER_LINES - 14
    rendered = list(tui._render_transcript())
    assert len(rendered) == 10
