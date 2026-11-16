"""Tests for JSONL persistence, batching, and the append/flush deadlock fix."""

from pathlib import Path

from src.core.history import ChatMessage, HistoryManager, Role


def make_msg(i: int) -> ChatMessage:
    return ChatMessage(role=Role.ME, timestamp="2026-11-16T00:00:00", content=f"msg-{i}")


async def test_batch_flush_writes_to_disk(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    hm = HistoryManager(path, batch_size=3, flush_interval=999)
    await hm.initialize()
    try:
        for i in range(3):
            await hm.append_message(make_msg(i))  # triggers flush at batch_size
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        assert "msg-0" in lines[0] and "msg-2" in lines[2]
    finally:
        await hm.shutdown()


async def test_append_then_shutdown_flushes_remainder(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    hm = HistoryManager(path, batch_size=100, flush_interval=999)
    await hm.initialize()
    try:
        for i in range(5):
            await hm.append_message(make_msg(i))
        assert not path.exists()  # still buffered, nothing written yet
        await hm.shutdown()
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 5
    finally:
        if hm._flush_task and not hm._flush_task.done():
            hm._flush_task.cancel()


async def test_load_history_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    hm = HistoryManager(path, batch_size=1, flush_interval=999)
    await hm.initialize()
    try:
        for i in range(4):
            await hm.append_message(make_msg(i))
        loaded = [m async for m in hm.load_history()]
        assert [m.content for m in loaded] == ["msg-0", "msg-1", "msg-2", "msg-3"]
        assert all(m.role is Role.ME for m in loaded)
    finally:
        await hm.shutdown()


async def test_corrupted_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "history.jsonl"
    path.write_text(
        '{"role": "ME", "timestamp": "t", "content": "good"}\n'
        "this is not json\n"
        '{"role": "ME", "timestamp": "t", "content": "also good"}\n',
        encoding="utf-8",
    )
    hm = HistoryManager(path)
    await hm.initialize()
    loaded = [m async for m in hm.load_history()]
    assert [m.content for m in loaded] == ["good", "also good"]
    await hm.shutdown()


async def test_missing_history_file_yields_nothing(tmp_path: Path) -> None:
    hm = HistoryManager(tmp_path / "does-not-exist.jsonl")
    await hm.initialize()
    loaded = [m async for m in hm.load_history()]
    assert loaded == []
    await hm.shutdown()
