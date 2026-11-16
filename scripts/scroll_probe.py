"""Verify transcript scrolling through a real pty: keyboard, wheel and fallback keys.

Runs `src/ui.tui.ChatTUI` inside a pseudo-terminal, feeds PageUp/PageDown,
Ctrl+Home/End, Ctrl+Up/Down and xterm SGR wheel sequences, then parses the
resulting screen with pyte. Exits 0 when every assertion holds.

    uv run python scripts/scroll_probe.py
"""

from __future__ import annotations

import fcntl
import os
import pty
import re
import select
import struct
import subprocess
import sys
import termios
import time

import pyte

APP = """
import asyncio
import os
import sys

from src.ui.tui import ChatTUI, STYLE_ME, STYLE_THEM

if os.environ.get("PROBE_TRACE"):
    from prompt_toolkit.key_binding import key_processor

    _orig_get = key_processor.KeyProcessor._get_matches
    _orig_prefix = key_processor.KeyProcessor._is_prefix_of_longer_match

    def _trace_get_matches(self, key_presses):
        matches = _orig_get(self, key_presses)
        print("MATCH", [tuple(k.key for k in key_presses)],
              [b.handler.__name__ for b in matches], file=sys.stderr, flush=True)
        return matches

    def _trace_prefix(self, key_presses):
        r = _orig_prefix(self, key_presses)
        print("PREFIX", [tuple(k.key for k in key_presses)], r, file=sys.stderr, flush=True)
        return r

    _orig_call = key_processor.KeyProcessor._call_handler

    def _trace_call(self, handler, key_sequence):
        print("CALL", handler.handler.__name__, handler.eager(), file=sys.stderr, flush=True)
        return _orig_call(self, handler, key_sequence)

    key_processor.KeyProcessor._get_matches = _trace_get_matches
    key_processor.KeyProcessor._is_prefix_of_longer_match = _trace_prefix
    key_processor.KeyProcessor._call_handler = _trace_call

async def main():
    if os.environ.get("PROBE_TRACE"):
        from src.ui import tui as tui_mod

        _orig_scroll = tui_mod.ChatTUI._scroll_by

        def _trace_scroll(self, delta):
            before = self._scroll
            _orig_scroll(self, delta)
            print(f"SCROLL_BY delta={delta} {before} -> {self._scroll} max={self._max_scroll()}",
                  file=sys.stderr, flush=True)

        tui_mod.ChatTUI._scroll_by = _trace_scroll

    tui = ChatTUI(status_provider=lambda: ("probe-peer", True))
    for i in range(80):
        style = STYLE_THEM if i % 2 else STYLE_ME
        tui.add_message(style, f"{i % 10}: line {i}")

    async def feed():
        # Messages that arrive while the user is scrolled up must not move the
        # view: they only show up as a hint and a counter in the status line.
        await asyncio.sleep(3.0)
        for n in range(3):
            tui.add_message(STYLE_THEM, f"arrived {n}")
            await asyncio.sleep(0.2)

    asyncio.create_task(feed())
    await tui.run()

asyncio.run(main())
"""

# Sequences as real terminals emit them.
WHEEL_UP = b"\x1b[<4;20;12M"
WHEEL_DOWN = b"\x1b[<5;20;12M"
PAGE_UP = b"\x1b[5~"
PAGE_DOWN = b"\x1b[6~"
CTRL_HOME = b"\x1b[1;5H"
CTRL_END = b"\x1b[1;5F"
# xterm encoding for Ctrl+Up/Down; some terminals use the CSI-u form.
CTRL_UP = b"\x1b[1;5A"
CTRL_UP_KITTY = b"\x1b[1;5u"
CTRL_DOWN = b"\x1b[1;5B"
QUIT = b"\x03"


def indicator(screen: pyte.Screen) -> int:
    """Parse the `[↑ N]` scroll indicator from the status line (0 if absent)."""
    match = re.search(r"\u2191\s*(\d+)", screen.display[0])
    return int(match.group(1)) if match else 0


def run_case(rows: int, cols: int) -> list[tuple[str, bool]]:
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    err_log = open(f"/tmp/opencode/probe_trace_{rows}x{cols}.txt", "w")
    proc = subprocess.Popen(
        [sys.executable, "-c", APP],
        stdin=slave,
        stdout=slave,
        stderr=err_log,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    os.close(slave)

    screen = pyte.Screen(cols, rows)
    stream = pyte.Stream(screen)

    def pump(seconds: float = 0.5) -> None:
        end = time.time() + seconds
        while time.time() < end:
            ready, _, _ = select.select([master], [], [], 0.1)
            if not ready:
                continue
            try:
                data = os.read(master, 4096)
            except OSError:
                return
            if not data:
                return
            stream.feed(data.decode("utf-8", errors="replace"))

    def send(seq: bytes, label: str) -> int:
        os.write(master, seq)
        pump(0.4)
        offset = indicator(screen)
        print(f"{label:<26} scroll offset = {offset}")
        return offset

    pump(1.5)
    checks: list[tuple[str, bool]] = []

    checks.append(("initial view is the tail", indicator(screen) == 0))

    page_up = send(PAGE_UP * 2, "PageUp x2")
    checks.append(("PageUp scrolls up", page_up > 0))

    wheel_up = send(WHEEL_UP * 3, "wheel up x3")
    checks.append(("wheel up scrolls up", wheel_up == page_up + 9))

    wheel_down = send(WHEEL_DOWN, "wheel down x1")
    checks.append(("wheel down scrolls down", wheel_down == wheel_up - 3))

    ctrl_up = send(CTRL_UP, "Ctrl+Up (xterm)")
    checks.append(("Ctrl+Up scrolls up", ctrl_up == wheel_down + 3))
    # prompt_toolkit 3.0.53 does not parse CSI-u arrow-with-modifier forms,
    # so this is informational only.
    send(CTRL_UP_KITTY, "Ctrl+Up (CSI-u)")

    top = send(CTRL_HOME, "Ctrl+Home")
    checks.append(("Ctrl+Home jumps to top", top > ctrl_up))

    tail = send(CTRL_END, "Ctrl+End")
    checks.append(("Ctrl+End returns to tail", tail == 0))

    # Messages arriving while scrolled up must not move the view.
    pump(2.5)
    send(PAGE_UP, "PageUp after arrivals")
    pump(0.5)
    status = screen.display[0]
    transcript = "\n".join(screen.display)
    print(f"status line: {status!r}")
    checks.append(("status shows new-below counter", "new below" in status))
    checks.append(("transcript hints at new lines", "new line(s) below" in transcript))
    restored = send(PAGE_DOWN, "PageDown restores tail")
    checks.append(("PageDown returns to tail", restored == 0))

    os.write(master, QUIT)
    pump(2.0)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    if proc.returncode != 0:
        print("returncode:", proc.returncode)

    return checks


def main() -> int:
    all_checks: list[tuple[str, bool]] = []
    for rows, cols in ((24, 80), (12, 40)):
        print(f"\n=== terminal {rows}x{cols} ===")
        all_checks.extend(run_case(rows, cols))

    print("\n=== scroll probe ===")
    for name, ok in all_checks:
        print(f"[{'OK' if ok else 'FAIL'}] {name}")

    failed = [name for name, ok in all_checks if not ok]
    print("SCROLL PROBE OK" if not failed else f"SCROLL PROBE FAILED: {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
