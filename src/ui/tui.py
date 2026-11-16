"""Chat TUI built on prompt_toolkit.

Layout:
  ┌ status line: localX ⇄ <peer> ONLINE/OFFLINE (+ scroll indicator)
  ├ transcript: pre-wrapped, scrollable tail of the buffer
  └ input field: " >> "

Scrolling:
  PageUp / PageDown — move through history, Ctrl+Home/End jump to top/bottom.
  Mouse wheel — scroll three lines per notch over the transcript.
  The scroll offset resets when you send a message.
"""

from __future__ import annotations

import asyncio
import textwrap
from typing import Callable, Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings import mouse as _pt_mouse_bindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.mouse_events import (
    MouseButton,
    MouseModifier,
    MouseEvent,
    MouseEventType,
)
from prompt_toolkit.widgets import TextArea

MAX_BUFFER_LINES = 1000

STYLE_ME = "ansibrightgreen"
STYLE_THEM = "ansibrightblue"
STYLE_HISTORY = "ansibrightblack"
STYLE_SYSTEM = "ansibrightyellow"
STYLE_DIM = "ansibrightblack"
STYLE_ONLINE = "ansibrightgreen"
STYLE_OFFLINE = "ansibrightred"

WHEEL_STEP = 3  # transcript lines per mouse-wheel notch

_MOD_BITS = {
    0: frozenset(),
    4: frozenset({MouseModifier.SHIFT}),
    8: frozenset({MouseModifier.ALT}),
    12: frozenset({MouseModifier.SHIFT, MouseModifier.ALT}),
    16: frozenset({MouseModifier.CONTROL}),
    20: frozenset({MouseModifier.SHIFT, MouseModifier.CONTROL}),
    24: frozenset({MouseModifier.ALT, MouseModifier.CONTROL}),
    28: frozenset({MouseModifier.SHIFT, MouseModifier.ALT, MouseModifier.CONTROL}),
}


def _patch_wheel_codes() -> None:
    """Teach prompt_toolkit the real xterm SGR wheel codes.

    Terminals report wheel notches as `ESC [ < 4 ; x ; y M` (up) and
    `ESC [ < 5 ; x ; y M` (down). prompt_toolkit 3.0.53 maps 4/5 to
    "shift + left/middle click" and expects scroll at 64/65, so the wheel
    never reaches any scroll handler. Re-map 4/5 (plus modifier variants)
    onto SCROLL_UP / SCROLL_DOWN; the 64/65 entries are left in place for
    terminals that use them.
    """
    table = _pt_mouse_bindings.xterm_sgr_mouse_events
    for base, event_type in (
        (4, MouseEventType.SCROLL_UP),
        (5, MouseEventType.SCROLL_DOWN),
    ):
        for bits in _MOD_BITS:
            table[(base + bits, "M")] = (MouseButton.NONE, event_type, _MOD_BITS[bits])


_patch_wheel_codes()


class TranscriptControl(FormattedTextControl):
    """Transcript surface that also handles mouse-wheel scrolling.

    prompt_toolkit routes mouse events to the control covering the clicked
    cell. `FormattedTextControl` only looks for per-fragment handlers, so a
    wheel event would fall through to the generic `Window` scroll, which
    conflicts with the manual tail rendering this TUI uses. Handling it here
    keeps keyboard and wheel scrolling on the same `_scroll` state.
    """

    def __init__(self, text: Callable[[], FormattedText], scroll: Callable[[int], None]) -> None:
        super().__init__(text=text)
        self._scroll = scroll

    def mouse_handler(self, mouse_event: MouseEvent) -> "NotImplementedOrNone":
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            return self._scroll(WHEEL_STEP)
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            return self._scroll(-WHEEL_STEP)
        return NotImplemented


class ChatTUI:
    """Owns the terminal surface and forwards typed lines to the orchestrator."""

    def __init__(
        self,
        orchestrator=None,
        status_provider: Optional[Callable[[], tuple[str, bool]]] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.status_provider = status_provider
        self._buffer: list[tuple[str, str]] = []
        self._pending: list[asyncio.Task] = []
        self._scroll: int = 0
        self._unread: int = 0

        self.input_field = TextArea(
            height=1,
            multiline=False,
            prompt=" >> ",
            style="class:ChatInput",
        )

        # Transcript takes all remaining rows; lines are pre-wrapped by us.
        self.output_window = Window(
            content=TranscriptControl(self._render_transcript, self._scroll_by),
            style="class:ChatTranscript",
        )

        self.status_window = Window(
            content=FormattedTextControl(text=self._render_status),
            height=1,
            style="class:ChatStatus",
        )

        self.layout = Layout(
            HSplit([self.status_window, self.output_window, self.input_field])
        )

        self.kb = KeyBindings()

        @self.kb.add("enter")
        def _submit(event) -> None:
            text = self.input_field.text.strip()
            if not text:
                return
            self.input_field.text = ""
            self._scroll = 0
            self._dispatch(text)

        @self.kb.add("pageup")
        def _scroll_up(event) -> None:
            self._scroll_by(self._visible_rows())

        @self.kb.add("pagedown")
        def _scroll_down(event) -> None:
            self._scroll_by(-self._visible_rows())

        # Terminals without mouse reporting (e.g. alacritty) still get a
        # fine-grained wheel equivalent.
        @self.kb.add("c-up")
        def _wheel_up(event) -> None:
            self._scroll_by(WHEEL_STEP)

        @self.kb.add("c-down")
        def _wheel_down(event) -> None:
            self._scroll_by(-WHEEL_STEP)

        @self.kb.add("c-home")
        def _jump_top(event) -> None:
            self._scroll = self._max_scroll()

        @self.kb.add("c-end")
        def _jump_bottom(event) -> None:
            self._scroll = 0

        @self.kb.add("c-c")
        @self.kb.add("c-d")
        def _quit(event) -> None:
            event.app.exit()

        self.app: Optional[Application] = None

    # ------------------------------------------------------------ terminal size
    def _terminal_size(self) -> tuple[int, int]:
        """(rows available for transcript, usable columns)."""
        try:
            size = self.app.output.get_size()
            rows = max(1, size.rows - 2)  # status line + input line
            cols = max(20, size.columns - 1)
        except Exception:
            rows, cols = 24, 80
        return rows, cols

    def _visible_rows(self) -> int:
        rows, _ = self._terminal_size()
        return max(1, rows)

    def _scroll_by(self, delta: int) -> None:
        """Move the transcript view by `delta` lines: positive shows older text."""
        if delta == 0:
            return
        self._scroll = max(0, min(self._max_scroll(), self._scroll + delta))
        if self._scroll == 0:
            self._unread = 0
        if self.app is not None:
            self.app.invalidate()

    def _max_scroll(self) -> int:
        """Largest scroll offset that still keeps at least one line visible."""
        rows, cols = self._terminal_size()
        return max(0, len(self._wrapped_lines(cols)) - 1)

    # ------------------------------------------------------------- rendering
    def _wrapped_lines(self, cols: int) -> list[tuple[str, str]]:
        """Flatten the buffer into terminal-width display lines."""
        out: list[tuple[str, str]] = []
        for style, line in self._buffer:
            if not line:
                out.append((style, ""))
                continue
            for part in line.split("\n"):
                wrapped = textwrap.wrap(part, width=cols) or [""]
                out.extend((style, w) for w in wrapped)
        return out

    def _render_transcript(self) -> FormattedText:
        rows, cols = self._terminal_size()
        lines = self._wrapped_lines(cols)
        total = len(lines)

        end = max(0, total - self._scroll)
        start = max(0, end - rows)
        visible = lines[start:end]

        if start > 0:
            marker = (STYLE_DIM, f"  ... {start} line(s) above (PageUp)")
            visible = [marker] + visible[: max(0, rows - 1)]

        if self._unread and self._scroll > 0:
            hint = (STYLE_DIM, f"  ... {self._unread} new line(s) below (PageDown)")
            visible = visible[: max(0, rows - 1)] + [hint]

        if not visible:
            return FormattedText([])
        return FormattedText([(style, text + "\n") for style, text in visible])

    def _render_status(self) -> FormattedText:
        peer, online = self.status_provider() if self.status_provider else ("peer", False)
        state = "ONLINE" if online else "OFFLINE"
        style = STYLE_ONLINE if online else STYLE_OFFLINE
        parts: list[tuple[str, str]] = [("bold", " localX "), ("", f" peer: {peer} "), (style, state)]
        if self._scroll > 0:
            indicator = f"  [↑ {self._scroll}]"
            if self._unread:
                indicator += f" {self._unread} new below"
            parts.append(("ansibrightblack", indicator))
        return FormattedText(parts)

    # --------------------------------------------------------------- buffer ops
    def add_message(self, style: str, text: str) -> None:
        self._buffer.append((style, text))
        if len(self._buffer) > MAX_BUFFER_LINES:
            del self._buffer[: len(self._buffer) - MAX_BUFFER_LINES]
        if self._scroll > 0:
            self._unread += 1
        if self.app is not None:
            self.app.invalidate()

    def add_system(self, text: str) -> None:
        self._buffer.append((STYLE_SYSTEM, f"[ SYSTEM ] {text}"))
        if self._scroll > 0:
            self._unread += 1
        if self.app is not None:
            self.app.invalidate()

    # ----------------------------------------------------------- input routing
    def _dispatch(self, text: str) -> None:
        if self.orchestrator is None:
            return
        task = asyncio.create_task(self.orchestrator.handle_input(text))
        self._pending.append(task)

    async def run(self) -> None:
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
        )
        await self.app.run_async()
        for task in self._pending:
            task.cancel()
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)


# Backwards-compatible alias used by older wiring.
TUI = ChatTUI
