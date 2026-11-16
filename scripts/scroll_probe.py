"""Verify transcript scrolling through a real pty: keyboard and mouse wheel.

Runs `src/ui/tui.py`'s ChatTUI inside a pseudo-terminal, feeds PageUp/PageDown,
Ctrl+Home/End and xterm SGR wheel sequences, and parses the resulting screen
with pyte. Exits 0 when all assertions hold.

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

ROWS, COLS = 24, 80
APP = """
import asyncio
from src.ui.tui import ChatTUI, STYLE_ME, STYLE_THEM

async def main():
    tui = ChatTUI(status_provider=lambda: ("probe-peer", True))
    for i in range(80):
        style = STYLE_THEM if i % 2 else STYLE_ME
        tui.add_message(style, f"{i % 10}: line {i}")

    async def feed():
        # Messages that arrive while the user is scrolled up must not move the view.
        await asyncio.sleep(3.0)
        for n in range(3):
            tui.add_message(STYLE_THEM, f"arrived {n}")
            await asyncio.sleep(0.2)

    asyncio.create_task(feed())
    await tui.run()

asyncio.run(main())
"""

WHEEL_UP = b"\x1b[<4;20;12M"
WHEEL_DOWN = b"\x1b[<5;20;12M"
PAGE_UP = b"\x1b[5~"
PAGE_DOWN = b"\x1b[6~"
CTRL_HOME = b"\x1b[1;5H"
CTRL_END = b"\x1b[1;5F"
QUIT = b"\x03"


def indicator(screen: pyte.Screen) -> int:
    """Parse the `[↑ N]` scroll indicator from the status line (0 if absent)."""
    match = re.search(r"\u2191\s*(\d+)", screen.display[0])
    return int(match.group(1)) if match else 0


def main() -> int:
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))

    proc = subprocess.Popen(
        [sys.executable, "-c", APP],
        stdin=slave,
        stdout=slave,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    os.close(slave)

    screen = pyte.Screen(COLS, ROWS)
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
        print(f"{label:<22} scroll offset = {offset}")
        return offset

    pump(1.5)
    checks: list[str] = []

    offset = indicator(screen)
    checks.append(("initial view is the tail", offset == 0))

    page_up = send(PAGE_UP * 2, "PageUp x2")
    checks.append(("PageUp scrolls up", page_up > 0))

    wheel_up = send(WHEEL_UP * 3, "wheel up x3")
    checks.append(("wheel up scrolls up", wheel_up == page_up + 9))

    wheel_down = send(WHEEL_DOWN, "wheel down x1")
    checks.append(("wheel down scrolls down", wheel_down == wheel_up - 3))

    top = send(CTRL_HOME, "Ctrl+Home")
    checks.append(("Ctrl+Home jumps to top", top > wheel_up))

    tail = send(CTRL_END, "Ctrl+End")
    checks.append(("Ctrl+End returns to tail", tail == 0))

    # Messages arriving while scrolled up must not move the view: they show up as
    # a hint in the transcript and a counter in the status line.
    pump(2.5)
    scrolled = send(PAGE_UP, "PageUp after arrivals")
    pump(0.5)
    status = screen.display[0]
    transcript = "\n".join(screen.display)
    checks.append(("status shows new-below counter", "new below" in status))
    checks.append(("transcript hints at new lines", "new line(s) below" in transcript))
    restored = send(PAGE_DOWN, "PageDown restores tail")
    checks.append(("PageDown returns to tail", restored == 0))

    os.write(master, QUIT)
    pump(2.0)
    proc.wait(timeout=5)
    if proc.returncode != 0:
        print("stderr:", proc.stderr.read().decode()[:400])

    print("\n=== scroll probe ===")
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"[{'OK' if ok else 'FAIL'}] {name}")
    print("SCROLL PROBE OK" if not failed else f"SCROLL PROBE FAILED: {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
