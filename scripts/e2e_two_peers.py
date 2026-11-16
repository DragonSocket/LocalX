"""End-to-end check: two real localX peers in pseudo-terminals exchange messages."""

import os
import pty
import select
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def spawn(peer_id: str, local_port: int, remote_port: int, history: str):
    env = os.environ.copy()
    env.update(
        LOCALX_NODE_PEER_ID=peer_id,
        LOCALX_LOCAL_PORT=str(local_port),
        LOCALX_REMOTE_PORT=str(remote_port),
        LOCALX_STORAGE_HISTORY_FILE=history,
    )
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        [sys.executable, "src/main.py"],
        cwd=str(ROOT),
        stdin=slave,
        stdout=slave,
        stderr=subprocess.PIPE,
        env=env,
    )
    os.close(slave)
    return proc, master


def read_chunk(master: int, timeout: float = 3.0) -> str:
    out = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 0.2)
        if r:
            try:
                out += os.read(master, 4096)
            except OSError:
                break
        if b" >> " in out:
            break
    return out.decode("utf-8", errors="replace")


def main() -> int:
    a, ma = spawn("alice", 9101, 9102, "history_alice.jsonl")
    b, mb = spawn("bob", 9102, 9101, "history_bob.jsonl")

    head_a = read_chunk(ma)
    head_b = read_chunk(mb)
    print("alice UI ready:", " >> " in head_a)
    print("bob UI ready:  ", " >> " in head_b)

    time.sleep(2.0)  # let the connector reconnect loop settle

    os.write(ma, b"ping-from-alice\n")
    time.sleep(1.5)
    os.write(mb, b"pong-from-bob\n")
    time.sleep(1.5)

    os.write(mb, b"/status\n")
    os.write(mb, b"/exit\n")
    time.sleep(1.5)
    os.write(ma, b"/exit\n")
    time.sleep(1.5)

    tail_b = read_chunk(mb, 2.0)
    tail_a = read_chunk(ma, 2.0)

    for p in (a, b):
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            p.kill()

    err_a = a.stderr.read().decode("utf-8", "replace")
    err_b = b.stderr.read().decode("utf-8", "replace")

    ok = ("ping-from-alice" in tail_b) and ("pong-from-bob" in tail_a)
    print("alice saw bob's message:", "pong-from-bob" in tail_a)
    print("bob saw alice's message:", "ping-from-alice" in tail_b)
    if not ok:
        print("A stderr:", err_a[-1500:])
        print("B stderr:", err_b[-1500:])
        print("A tail:", tail_a[-800:])
        print("B tail:", tail_b[-800:])
        return 1
    print("E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
