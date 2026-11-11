import asyncio
from typing import Any
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.application import get_app

class TUI:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.output_buffer = []
        self.app = None
        
        # Input area
        self.input_field = TextArea(
            height=1,
            multiline=False,
            prompt=" >> ",
        )

        # Output area
        self.output_control = lambda: self._get_output_text() # This is problematic in prompt_toolkit
        # Prompt_toolkit needs a proper TextControl
        from prompt_toolkit.layout.controls import FormattedTextControl
        self.output_control = FormattedTextControl(text=self._get_output_text)
        self.output_window = Window(content=self.output_control)

        # Layout
        self.layout = Layout(
            HSplit([
                self.output_window,
                self.input_field,
            ])
        )

        # Key bindings
        from prompt_toolkit.key_binding import KeyBindings
        self.kb = KeyBindings()

        @self.kb.add('c-c')
        def _(event):
            event.app.exit()

        @self.kb.add('enter')
        def _(event):
            text = self.input_field.text.strip()
            if text:
                # Schedule the command handling
                asyncio.create_task(self.orchestrator.handle_input(text))
                self.input_field.text = ""

        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True
        )

    def _get_output_text(self):
        # Returns list of (style, text) tuples
        return [(style, text + "\n") for style, text in self.output_buffer]

    async def add_message(self, style: str, text: str):
        self.output_buffer.append((style, text))
        if self.app:
            self.app.invalidate()
            # Auto-scroll to bottom
            self.app.layout.scroll_lines(self.output_window, 1000) # Move to bottom

    async def run_tui(self, orchestrator) -> None:
        await self.app.run_async()
