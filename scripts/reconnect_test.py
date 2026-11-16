"""Verify the offline outbox is flushed when the peer comes back online.

Scenario:
  Peer A: listens on 9101, connects to 9102 (peer B not started yet -> OFFLINE).
  A queues 3 messages while B is down.
  Peer B starts (listens on 9102, connects to 9101).
  A reconnects, flushes the outbox; B must receive all 3 messages.
"""

import asyncio
import logging
import sys

from src.core.config import AppConfig
from src.core.network import NetworkEngine

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

RECONNECT = 2  # engine reconnect delay is 3 s by default; we just wait


async def main() -> None:
    a_cfg = AppConfig(
        node={"peer_id": "alice"},
        local={"host": "127.0.0.1", "port": 9101},
        remote={"host": "127.0.0.1", "port": 9102},
        storage={"history_file": "/tmp/opencode/reconnect_alice.jsonl"},
    )
    b_cfg = AppConfig(
        node={"peer_id": "bob"},
        local={"host": "127.0.0.1", "port": 9102},
        remote={"host": "127.0.0.1", "port": 9101},
        storage={"history_file": "/tmp/opencode/reconnect_bob.jsonl"},
    )

    a = NetworkEngine()
    await a.start(a_cfg)

    # Give the connector a few failed attempts so alice is definitively offline.
    await asyncio.sleep(4)
    assert not a.peer_online, "alice should see bob offline"

    for i in range(3):
        status = await a.send_message(f"queued-{i}")
        assert status == "queued", f"expected queued, got {status}"
    print(f"alice queued {a.queued_count()} messages while bob is offline")

    b = NetworkEngine()
    await b.start(b_cfg)

    received = []

    async def pump():
        async for env in b.listen():
            received.append(env.payload)
            if len(received) >= 3:
                return

    await asyncio.wait_for(pump(), timeout=15)

    await asyncio.sleep(0.5)
    assert a.queued_count() == 0, "outbox should be empty after flush"
    assert received == ["queued-0", "queued-1", "queued-2"], f"got {received}"
    print("RECONNECT/OUTBOX TEST OK: bob received", received)

    await a.stop()
    await b.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("RECONNECT/OUTBOX TEST FAILED:", e)
        sys.exit(1)
