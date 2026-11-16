"""Full-screen chat UI built on prompt_toolkit.

Design notes:
- The transcript is a bounded in-memory buffer (`MAX_BUFFER_LINES`).
- The output window always renders the *tail* of the buffer, sized to the
  terminal height, so the newest message is visible without scrolling hacks.
- Rendering is done with `FormattedTextControl`, which accepts a callable that
  returns a list of (style, text) fragments.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.widgets import TextArea

MAX_BUFFER_LINES = 1000

STYLE_ME = "ansibrightgreen"
STYLE_THEM = "ansibrightblue"
STYLE_HISTORY = "ansibrightblack"
STYLE_SYSTEM = "ansibrightyellow"
STYLE_STATUS = "gray"


class ChatTUI:
    """Owns the terminal surface and forwards typed lines to the orchestrator."""

    def __init__(self, orchestrator=None) -> None:
        self.orchestrator = orchestrator
        self._buffer: list[tuple[str, str]] = []
        self._pending: list[asyncio.Task] = []

        self.input_field = TextArea(
            height=1,
            multiline=False,
            prompt=" >> ",
            style="class:ChatInput",
        )

        self.output_window = Window(
            content=FormattedTextControl(text=self._render_transcript),
            wrap_lines=True,
            style="class:ChatTranscript",
        )

        status_window = Window(
            content=FormattedTextControl(text=self._render_status),
            height=1,
            style="class:ChatStatus",
        )

        self.layout = Layout(
            HSplit([status_window, self.output_window, self.input_field])
        )

        self.kb = KeyBindings()

        @self.kb.add("enter")
        def _submit(event) -> None:
            text = self.input_field.text.strip()
            if not text:
                return
            self.input_field.text = ""
            self._dispatch(text)

        @self.kb.add("c-c")
        @self.kb.add("c-d")
        def _quit(event) -> None:
            event.app.exit()

        self.app: Optional[Application] = None

    # ------------------------------------------------------------------ buffer
    def _available_height(self) -> int:
        """Rows usable by the transcript window (best-effort, terminal-aware)."""
        try:
            total_rows = self.app.output.get_size().rows
        except Exception:
            total_rows = 24
        # status line + input line + a little breathing room
        return max(1, total_rows - 2)

    def _render_transcript(self):
        visible = self._buffer[-self._available_height():]
        fragments = [(style, f"{line}\n") for style, line in visible]
        return FormattedText(fragments) if fragments else FormattedText([("class:dim", "")])

    def _render_status(self) -> FormattedText:
        return FormattedText([(STYLE_STATUS, " localX ")])

    async def add_message(self, style: str, text: str) -> None:
        self._buffer.append((style, text))
        if len(self._buffer) > MAX_BUFFER_LINES:
            del self._buffer[: len(self._buffer) - MAX_BUFFER_LINES]
        if self.app is not None:
            self.app.invalidate()

    def add_system(self, text: str) -> None:
        self._buffer.append((STYLE_SYSTEM, f"[ SYSTEM ] {text}"))
        if self.app is not None:
            self.app.invalidate()

    # ------------------------------------------------------------- input routing
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
        await asyncio.gather(*self._pending, return_exceptions=True)


# Backwards-compatible alias used by older wiring.
TUI = ChatTUI
