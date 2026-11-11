import asyncio
import logging
import os
import signal
import subprocess
from enum import Enum
from typing import AsyncIterator, Optional
from src.core.exceptions import AppError, NetworkConnectionError, NetworkProcessError, NetworkInvalidStateError
from src.core.config import ConnectionConfig

logger = logging.getLogger(__name__)

class NetworkState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"

class NetworkEngine:
    def __init__(self):
        self._state = NetworkState.IDLE
        self._process: Optional[asyncio.subprocess.Process] = None
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=500)
        self._reader_task: Optional[asyncio.Task] = None
        self._error_event = asyncio.Event()

    @property
    def state(self) -> NetworkState:
        return self._state

    async def start(self, config: ConnectionConfig) -> None:
        if self._state != NetworkState.IDLE:
            raise NetworkInvalidStateError(f"Cannot start from state {self._state}")

        logger.info(f"Starting ncat connection to {config.host}:{config.port}")
        
        try:
            self._state = NetworkState.RUNNING
            self._process = await asyncio.create_subprocess_exec(
                "ncat", config.host, str(config.port),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setpgrp # Create a new process group
            )
            
            self._reader_task = asyncio.create_task(self._read_loop())
            
            # Monitor process exit in background
            asyncio.create_task(self._monitor_process())

        except Exception as e:
            self._state = NetworkState.IDLE
            logger.error(f"Failed to start ncat: {e}")
            raise NetworkConnectionError(f"Could not connect to {config.host}:{config.port}: {e}")

    async def _read_loop(self) -> None:
        """Reads from stdout and stderr."""
        try:
            while self._state == NetworkState.RUNNING and self._process:
                # We use wait_for or similar to ensure we handle the stream efficiently
                line_bytes = await self._process.stdout.readline()
                if not line_bytes:
                    break
                
                line = line_bytes.decode('utf-8', errors='replace').strip()
                if line:
                    # Implement "Drop-Oldest" Backpressure
                    if self._queue.full():
                        try:
                            self._queue.get_nowait()
                            logger.warning("Network queue full. Dropping oldest message.")
                        except asyncio.QueueEmpty:
                            pass
                    
                    await self._queue.put(line)

        except Exception as e:
            logger.error(f"Error in Network read loop: {e}")
        finally:
            logger.info("Network read loop terminated.")

    async def _monitor_process(self) -> None:
        """Monitors the subprocess for unexpected termination."""
        if not self._process:
            return
        
        return_code = await self._process.wait()
        if self._state == NetworkState.RUNNING:
            logger.error(f"ncat process exited unexpectedly with code {return_code}")
            self._state = NetworkState.IDLE
            # In a real app, we might notify the orchestrator here via an event
            self._error_event.set()

    async def send_message(self, content: str) -> None:
        if self._state != NetworkState.RUNNING or not self._process:
            raise NetworkInvalidStateError("Network is not running.")
        
        try:
            self._process.stdin.write((content + "\n").encode('utf-8'))
            await self._process.stdin.drain()
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise NetworkProcessError(f"Error writing to ncat stdin: {e}")

    async def listen(self) -> AsyncIterator[str]:
        """Yields messages from the queue."""
        while self._state == NetworkState.RUNNING or not self._queue.empty():
            try:
                # Use a timeout so we can check the state periodically
                msg = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                yield msg
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in listen iterator: {e}")
                break

    async def stop(self) -> None:
        if self._state == NetworkState.IDLE:
            return

        logger.info("Stopping NetworkEngine...")
        self._state = NetworkState.STOPPING

        if self._process:
            try:
                # Kill the entire process group
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                
                # Give it a moment to die gracefully
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    logger.warning("ncat did not respond to SIGTERM, sending SIGKILL.")
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                    await self._process.wait()
            except Exception as e:
                logger.error(f"Error during process shutdown: {e}")

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        self._state = NetworkState.IDLE
        logger.info("NetworkEngine stopped.")
