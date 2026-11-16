import asyncio
import json
import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, List, Optional
from dataclasses import dataclass, asdict
import portalocker
from src.core.exceptions import AppError, HistoryLoadError, HistoryWriteError

logger = logging.getLogger(__name__)

class Role(str, Enum):
    ME = "ME"
    THEM = "THEM"

@dataclass(frozen=True)
class ChatMessage:
    role: Role
    timestamp: str  # ISO 8601
    content: str
    version: int = 1

class HistoryManager:
    def __init__(self, file_path: Path, batch_size: int = 10, flush_interval: float = 5.0):
        self.file_path = file_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer: List[ChatMessage] = []
        self._buffer_lock = asyncio.Lock()
        self._file_lock_name = f"{file_path}.lock"
        self._executor = None
        self._loop = None
        self._flush_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the executor and start the background flush task."""
        self._loop = asyncio.get_running_loop()
        from concurrent.futures import ThreadPoolExecutor
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def load_history(self) -> AsyncIterator[ChatMessage]:
        """Streams messages from the JSONL file."""
        if not self.file_path.exists():
            return

        try:
            # Use executor for reading to avoid blocking the loop
            def _read_sync():
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return f.readlines()

            lines = await self._loop.run_in_executor(self._executor, _read_sync)
            
            for line in lines:
                try:
                    data = json.loads(line)
                    # Create object (assuming simple mapping)
                    msg = ChatMessage(
                        role=Role(data["role"]),
                        timestamp=data["timestamp"],
                        content=data["content"],
                        version=data.get("version", 1)
                    )
                    yield msg
                except Exception as e:
                    logger.warning(f"Skipping corrupted history line: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            raise HistoryLoadError(f"Could not read history file: {e}")

    async def append_message(self, message: ChatMessage) -> None:
        """Adds message to buffer and flushes if batch_size is reached."""
        async with self._buffer_lock:
            self._buffer.append(message)
            if len(self._buffer) >= self.batch_size:
                # NOTE: flush() re-acquires _buffer_lock, which would deadlock.
                await self._flush_locked()

    async def flush(self) -> None:
        """Writes the buffer to disk."""
        async with self._buffer_lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        """Must be called while _buffer_lock is held."""
        if not self._buffer:
            return

        to_write = list(self._buffer)
        self._buffer.clear()

        try:
            await self._loop.run_in_executor(self._executor, self._sync_flush, to_write)
        except Exception as e:
            # Put the batch back at the front of the buffer so nothing is
            # lost: the next flush (retry) will attempt the same messages again.
            self._buffer[:0] = to_write
            logger.error(f"Flush failed, batch re-queued ({len(to_write)} msgs): {e}")
            raise HistoryWriteError(f"Failed to flush history to disk: {e}")

    def _sync_flush(self, messages: List[ChatMessage]) -> None:
        """Synchronous write operation to be run in executor."""
        with portalocker.Lock(self.file_path, mode='a', timeout=5):
            with open(self.file_path, mode='a', encoding="utf-8") as f:
                for msg in messages:
                    f.write(json.dumps(asdict(msg)) + "\n")

    async def _periodic_flush(self) -> None:
        """Background task to ensure data is written even if batch is not full."""
        try:
            while True:
                await asyncio.sleep(self.flush_interval)
                if self._buffer:
                    await self.flush()
        except asyncio.CancelledError:
            # Expected when shutting down
            pass

    async def shutdown(self) -> None:
        """Final flush and cleanup."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush for remaining messages
        if self._buffer:
            await self.flush()
            
        if self._executor:
            self._executor.shutdown(wait=True)
        logger.info("HistoryManager shutdown complete.")
