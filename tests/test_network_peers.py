import asyncio
import json

from src.core.network import NetworkEngine, NetworkState


def _line(sender: str, payload: str, kind: str = "message") -> str:
    return json.dumps({"sender_id": sender, "payload": payload, "kind": kind, "version": 1})


async def test_peers_forgotten_when_stream_ends():
    """Audit #3/#18: peer status must reflect live streams, not history."""
    engine = NetworkEngine()
    engine._peer_id = "me"
    engine._state = NetworkState.RUNNING

    stream = "\n".join([
        _line("bob", "", "hello"),
        _line("bob", "hi"),
        _line("carol", "", "hello"),
    ])
    proc = await asyncio.create_subprocess_exec(
        "printf", "%s\n" % stream,
        stdout=asyncio.subprocess.PIPE,
    )
    await engine._read_stream(proc, "connector")

    assert engine.known_peers == set()
    assert engine.remote_peer_id is None
    assert engine._peers_by_source == {}
    engine._state = NetworkState.IDLE


async def test_peer_tracked_while_stream_alive():
    engine = NetworkEngine()
    engine._peer_id = "me"
    engine._state = NetworkState.RUNNING

    proc = await asyncio.create_subprocess_exec(
        "sh", "-c", "printf '%s\\n' '{\"sender_id\":\"bob\",\"payload\":\"\",\"kind\":\"hello\",\"version\":1}'; sleep 5",
        stdout=asyncio.subprocess.PIPE,
    )
    task = asyncio.create_task(engine._read_stream(proc, "connector"))
    await asyncio.sleep(0.3)
    assert engine.known_peers == {"bob"}
    assert engine.remote_peer_id == "bob"

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    # finally-block of cancelled task runs, forgetting the source's peers
    assert engine.known_peers == set()
    engine._state = NetworkState.IDLE
    proc.kill()


class _FakeStdin:
    def __init__(self, fail_after: int):
        self.fail_after = fail_after
        self.written = 0

    def write(self, data: bytes) -> None:
        self.written += 1
        if self.written > self.fail_after:
            raise OSError("channel closed")

    async def drain(self) -> None:
        pass


async def test_flush_outbox_keeps_unsent_tail():
    """Audit #17: partial flush must not lose the unsent tail."""
    engine = NetworkEngine()
    engine._outbox = [_line("me", "a"), _line("me", "b"), _line("me", "c")]
    engine._connector = type("P", (), {"stdin": _FakeStdin(fail_after=1)})()

    await engine._flush_outbox()
    assert engine.queued_count() == 2
    assert engine._outbox[0] == _line("me", "b")


async def test_flush_outbox_retried_before_send():
    """Audit #6: a partial flush is retried on the next send, in order."""
    engine = NetworkEngine()
    engine._peer_id = "me"
    engine._state = NetworkState.RUNNING
    stdin = _FakeStdin(fail_after=0)  # always fails
    engine._connector = type("P", (), {"stdin": stdin, "returncode": None})()
    engine._outbox = [_line("me", "old")]

    # First send: flush fails, connector write fails -> both queued, order kept.
    assert await engine.send_message("new") == "queued"
    assert engine.queued_count() == 2
    assert engine._outbox[0] == _line("me", "old")

    engine._state = NetworkState.IDLE


async def test_send_after_dead_connector_queues():
    """Audit: a connector whose process exited must not be written to."""
    engine = NetworkEngine()
    engine._peer_id = "me"
    engine._state = NetworkState.RUNNING
    engine._connector = type("P", (), {"stdin": _FakeStdin(fail_after=99), "returncode": 1})()

    assert await engine.send_message("hello") == "queued"
    engine._state = NetworkState.IDLE


async def test_outbox_overflow_drops_oldest_instead_of_raising():
    """Audit #15: graceful degradation when the outbox is full."""
    engine = NetworkEngine()
    engine._peer_id = "me"
    engine._state = NetworkState.RUNNING
    engine._connector = None
    for i in range(200):
        await engine.send_message(f"msg {i}")
    assert engine.queued_count() == 200
    await engine.send_message("overflow")
    assert engine.queued_count() == 200
    assert engine._outbox[0] == _line("me", "msg 1")
    assert engine._outbox[-1] == _line("me", "overflow")
    engine._state = NetworkState.IDLE
