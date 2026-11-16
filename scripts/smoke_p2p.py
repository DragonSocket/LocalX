"""Local two-peer smoke test for the P2P transport.

Run with:  uv run python scripts/smoke_p2p.py
"""

import asyncio
import logging
import sys
from pathlib import Path

from src.core.config import AppConfig, NodeConfig, LocalConfig, RemoteConfig, StorageConfig
from src.core.network import NetworkEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s %(levelname)s: %(message)s",
    stream=sys.stderr,
)


def make_config(peer_id: str, local_port: int, remote_port: int) -> AppConfig:
    return AppConfig(
        node=NodeConfig(peer_id=peer_id),
        local=LocalConfig(host="127.0.0.1", port=local_port),
        remote=RemoteConfig(host="127.0.0.1", port=remote_port),
        storage=StorageConfig(history_file=Path("history_tmp.jsonl")),
    )


async def drain(engine: NetworkEngine, out: list[str]) -> None:
    async for env in engine.listen():
        out.append(f"{env.sender_id}: {env.payload}")


async def main() -> None:
    a = NetworkEngine(reconnect_delay=1.0)
    b = NetworkEngine(reconnect_delay=1.0)

    # Start B first to prove that a connector can wait for a listener.
    await b.start(make_config("bob", 9002, 9001))
    await asyncio.sleep(0.5)
    await a.start(make_config("alice", 9001, 9002))

    seen_a: list[str] = []
    seen_b: list[str] = []
    ta = asyncio.create_task(drain(a, seen_a))
    tb = asyncio.create_task(drain(b, seen_b))

    await asyncio.sleep(3.0)

    await a.send_message("hello from alice")
    await asyncio.sleep(0.5)
    await b.send_message("hi alice, from bob")
    await asyncio.sleep(1.0)

    print(f"alice saw: {seen_a}")
    print(f"bob saw:   {seen_b}")

    ok = (
        any("alice" in m and "hello from alice" in m for m in seen_b)
        and any("bob" in m and "hi alice" in m for m in seen_a)
    )

    print("handshake peers:", a.known_peers, b.known_peers)

    await a.stop()
    await b.stop()
    for t in (ta, tb):
        t.cancel()

    if not ok:
        print("SMOKE TEST FAILED")
        sys.exit(1)
    print("SMOKE TEST OK")


if __name__ == "__main__":
    asyncio.run(main())
