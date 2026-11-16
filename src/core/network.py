import asyncio
import json
import logging
import os
import signal
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Optional

from src.core.config import AppConfig
from src.core.exceptions import (
    NetworkConnectionError,
    NetworkInvalidStateError,
    NetworkProcessError,
)

logger = logging.getLogger(__name__)

# Envelope protocol shared by every peer. A line is one JSON object.
PROTOCOL_VERSION = 1


class NetworkState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"


@dataclass(frozen=True)
class Envelope:
    """Structured message exchanged between peers over ncat."""
    sender_id: str
    payload: str
    kind: str = "message"  # "hello" | "message"
    version: int = PROTOCOL_VERSION

    def to_line(self) -> str:
        return json.dumps(
            {
                "sender_id": self.sender_id,
                "payload": self.payload,
                "kind": self.kind,
                "version": self.version,
            },
            ensure_ascii=False,
        )


def parse_envelope(line: str) -> Optional[Envelope]:
    """Parse one protocol line. Returns None for malformed input."""
    try:
        data = json.loads(line)
        if not isinstance(data, dict):
            return None
        sender_id = str(data.get("sender_id", ""))
        payload = str(data.get("payload", ""))
        kind = str(data.get("kind", "message"))
        if not sender_id:
            return None
        return Envelope(sender_id=sender_id, payload=payload, kind=kind)
    except (json.JSONDecodeError, ValueError):
        return None


class NetworkEngine:
    """Dual-mode P2P transport built on `ncat`.

    - Listener mode: `ncat -l -k <local_host> <local_port>` accepts peers.
    - Connector mode: `ncat <remote_host> <remote_port>` sends to the peer,
      with automatic reconnect so either side can start first.
    """

    def __init__(self, reconnect_delay: float = 3.0):
        self._state = NetworkState.IDLE
        self._peer_id: str = ""
        self._reconnect_delay = reconnect_delay

        # Process handles
        self._listener: Optional[asyncio.subprocess.Process] = None
        self._connector: Optional[asyncio.subprocess.Process] = None

        # Background supervision tasks
        self._tasks: list[asyncio.Task] = []

        # Incoming envelopes (bounded -> natural backpressure)
        self._queue: asyncio.Queue[Envelope] = asyncio.Queue(maxsize=500)

        # Peer bookkeeping
        self._known_peers: set[str] = set()
        self._error_event = asyncio.Event()
        self._last_error: Optional[str] = None
        self._stop_sentinel = object()

    @property
    def state(self) -> NetworkState:
        return self._state

    @property
    def known_peers(self) -> set[str]:
        return set(self._known_peers)

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    async def start(self, config: AppConfig) -> None:
        if self._state != NetworkState.IDLE:
            raise NetworkInvalidStateError(f"Cannot start from state {self._state}")

        self._peer_id = config.node.peer_id
        self._state = NetworkState.RUNNING
        logger.info(
            "Peer '%s': listening on %s:%s, connecting to %s:%s",
            self._peer_id,
            config.local.host,
            config.local.port,
            config.remote.host,
            config.remote.port,
        )

        try:
            self._listener = await asyncio.create_subprocess_exec(
                "ncat",
                "-l",
                "-k",
                config.local.host,
                str(config.local.port),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setpgrp,  # own process group -> clean killpg teardown
            )
        except Exception as e:
            self._state = NetworkState.IDLE
            raise NetworkConnectionError(
                f"Could not start listener on {config.local.host}:{config.local.port}: {e}"
            ) from e

        self._tasks.append(asyncio.create_task(self._read_stream(self._listener, "listener")))
        self._tasks.append(asyncio.create_task(self._drain_stderr(self._listener, "listener")))
        self._tasks.append(asyncio.create_task(self._connect_loop(config)))

    async def _spawn_connector(self, config: AppConfig) -> Optional[asyncio.subprocess.Process]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ncat",
                config.remote.host,
                str(config.remote.port),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setpgrp,
            )
            # A failed connect makes ncat exit immediately; give it a moment and check.
            try:
                await asyncio.wait_for(proc.wait(), timeout=0.3)
            except asyncio.TimeoutError:
                pass  # still alive -> connection established
            if proc.returncode is not None:
                logger.warning(
                    "ncat could not reach peer at %s:%s (exit %s)",
                    config.remote.host,
                    config.remote.port,
                    proc.returncode,
                )
                return None
            return proc
        except Exception as e:
            logger.warning(
                "Connection to peer %s:%s failed: %s", config.remote.host, config.remote.port, e
            )
            return None

    async def _connect_loop(self, config: AppConfig) -> None:
        """Keep an outgoing channel to the remote peer alive."""
        while self._state == NetworkState.RUNNING:
            proc = await self._spawn_connector(config)
            if proc is None:
                self._last_error = (
                    f"Peer {config.remote.host}:{config.remote.port} unreachable, retrying"
                )
                self._error_event.set()
                await asyncio.sleep(self._reconnect_delay)
                continue

            self._connector = proc
            self._error_event.clear()
            logger.info("Connected to peer %s:%s", config.remote.host, config.remote.port)

            # Handshake so the remote peer knows who we are.
            try:
                proc.stdin.write((Envelope(sender_id=self._peer_id, payload="", kind="hello")
                                   .to_line() + "\n").encode("utf-8"))
                await proc.stdin.drain()
            except Exception as e:
                logger.error("Failed to send handshake: %s", e)

            self._tasks.append(asyncio.create_task(self._read_stream(proc, "connector")))
            self._tasks.append(asyncio.create_task(self._drain_stderr(proc, "connector")))

            await proc.wait()
            self._connector = None

            if self._state != NetworkState.RUNNING:
                break

            logger.info("Peer connection closed. Reconnecting...")
            await asyncio.sleep(self._reconnect_delay)

    async def _read_stream(self, proc: asyncio.subprocess.Process, source: str) -> None:
        """Read ncat stdout, parse envelopes, push them into the queue."""
        try:
            while self._state == NetworkState.RUNNING:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                envelope = parse_envelope(line)
                if envelope is None:
                    logger.warning("Dropped malformed line from %s: %r", source, line[:120])
                    continue

                # Never accept our own echoes: the listener broadcasts its stdin to
                # every client, so an outgoing copy can come back on another stream.
                if envelope.sender_id == self._peer_id:
                    logger.debug("Ignored self-echo from %s", source)
                    continue

                if envelope.kind == "hello":
                    self._known_peers.add(envelope.sender_id)
                    logger.info("Peer '%s' handshake received", envelope.sender_id)
                    continue

                self._known_peers.add(envelope.sender_id)
                # Bounded queue: `put` blocks when full -> natural backpressure.
                await self._queue.put(envelope)
        except Exception as e:
            logger.error("Error in %s read loop: %s", source, e)
        finally:
            logger.info("%s read loop terminated", source)

    async def _drain_stderr(self, proc: asyncio.subprocess.Process, source: str) -> None:
        """Consume stderr so the pipe never fills up and reports ncat diagnostics."""
        try:
            while True:
                line_bytes = await proc.stderr.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    logger.debug("ncat (%s): %s", source, line)
        except Exception:
            pass

    async def send_message(self, content: str, target_id: Optional[str] = None) -> None:
        if self._state != NetworkState.RUNNING:
            raise NetworkInvalidStateError("Network is not running.")

        envelope = Envelope(sender_id=self._peer_id, payload=content)

        if self._connector is None:
            raise NetworkInvalidStateError(
                "No peer connection is currently open. The remote peer is not listening yet."
            )

        # Outbound channel = the connector. Inbound channel = the listener.
        try:
            self._connector.stdin.write((envelope.to_line() + "\n").encode("utf-8"))
            await self._connector.stdin.drain()
        except Exception as e:
            logger.error("Failed to send message: %s", e)
            raise NetworkProcessError(f"Error writing to ncat stdin: {e}") from e

    async def listen(self) -> AsyncIterator[Envelope]:
        """Yield incoming envelopes until the engine is stopped."""
        while True:
            if self._state != NetworkState.RUNNING and self._queue.empty():
                break
            try:
                envelope = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Error in listen iterator: %s", e)
                break
            yield envelope
            self._queue.task_done()

    async def stop(self) -> None:
        if self._state == NetworkState.IDLE:
            return

        logger.info("Stopping NetworkEngine...")
        self._state = NetworkState.STOPPING

        for proc in (self._listener, self._connector):
            if proc is None or proc.returncode is not None:
                continue
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try:
                    await asyncio.wait_for(proc.wait(), timeout=3.0)
                except asyncio.TimeoutError:
                    logger.warning("ncat did not respond to SIGTERM, sending SIGKILL.")
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    await proc.wait()
            except ProcessLookupError:
                # Process already exited between the check and the kill.
                continue
            except Exception as e:
                logger.error("Error during process shutdown: %s", e)

        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()
        self._listener = None
        self._connector = None
        self._state = NetworkState.IDLE
        logger.info("NetworkEngine stopped.")
