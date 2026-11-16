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


def rendered_texts(tui: ChatTUI) -> list[str]:
    return [text for _, text in tui._render_transcript()]


def test_newest_line_survives_when_screen_is_full() -> None:
    """Regression: the indicator row used to eat the LAST line, so the newest
    message stayed invisible until the next one pushed it up."""
    tui = make_tui(rows=10, cols=20)
    fill(tui, 25)
    lines = rendered_texts(tui)
    assert len(lines) == 10
    assert "line-24" in lines[-1]
    assert any("above" in line for line in lines[:1])
    # nothing newer than the newest buffer line may be missing
    assert "line-23" in "".join(lines)


def test_newest_line_survives_with_below_hint() -> None:
    tui = make_tui(rows=10, cols=20)
    fill(tui, 25)
    tui._scroll = 5
    tui._unread = 3
    lines = rendered_texts(tui)
    assert len(lines) == 10
    assert "line-19" in lines[-2]  # newest visible content line
    assert "below" in lines[-1]


def test_view_never_shows_more_rows_than_the_screen() -> None:
    for rows in (3, 5, 10, 24):
        tui = make_tui(rows=rows, cols=20)
        fill(tui, 50)
        tui._scroll = tui._max_scroll() // 2
        tui._unread = 4
        assert len(rendered_texts(tui)) <= rows


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
