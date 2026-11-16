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

    Note on `-k`: the listener relays its stdin to ALL connected clients, so
    with 3+ instances the transport behaves as a group chat, not strict P2P.
    `/peers` reports the set of peers with live handshakes; the status line
    reflects whether at least one peer is connected.
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

        # Peer bookkeeping. Peers are remembered per stream source so that
        # when a stream dies its peers are forgotten — status never lies.
        self._known_peers: set[str] = set()
        self._peers_by_source: dict[str, set[str]] = {}
        self._remote_peer_id: Optional[str] = None
        self._last_error: Optional[str] = None
        self._stop_sentinel = object()

        # Messages typed while the peer was offline, flushed on reconnect.
        self._outbox: list[str] = []

    @property
    def state(self) -> NetworkState:
        return self._state

    @property
    def known_peers(self) -> set[str]:
        return set(self._known_peers)

    @property
    def remote_peer_id(self) -> Optional[str]:
        return self._remote_peer_id

    @property
    def peer_online(self) -> bool:
        """The remote peer is reachable and has completed the handshake."""
        return (
            self._state == NetworkState.RUNNING
            and self._connector is not None
            and bool(self._known_peers)
        )

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
                logger.debug(
                    "ncat could not reach peer at %s:%s (exit %s)",
                    config.remote.host,
                    config.remote.port,
                    proc.returncode,
                )
                return None
            return proc
        except Exception as e:
            logger.debug(
                "Connection to peer %s:%s failed: %s", config.remote.host, config.remote.port, e
            )
            return None

    async def _connect_loop(self, config: AppConfig) -> None:
        """Keep an outgoing channel to the remote peer alive."""
        attempt = 0
        while self._state == NetworkState.RUNNING:
            proc = await self._spawn_connector(config)
            if proc is None:
                # Exponential backoff: 2s, 4s, 8s ... capped at 15s.
                delay = min(self._reconnect_delay * (2**attempt), 15.0)
                attempt += 1
                self._last_error = (
                    f"Peer {config.remote.host}:{config.remote.port} unreachable, "
                    f"retrying in {delay:.0f}s"
                )
                await asyncio.sleep(delay)
                continue

            attempt = 0
            self._connector = proc
            self._last_error = None
            logger.info("Connected to peer %s:%s", config.remote.host, config.remote.port)

            # Handshake so the remote peer knows who we are.
            try:
                proc.stdin.write((Envelope(sender_id=self._peer_id, payload="", kind="hello")
                                   .to_line() + "\n").encode("utf-8"))
                await proc.stdin.drain()
            except Exception as e:
                logger.error("Failed to send handshake: %s", e)

            # Anything typed while the peer was offline goes out now.
            await self._flush_outbox()

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
            while True:
                # Drain grace period: after stop() we keep parsing buffered
                # lines until EOF or 1s of silence, so late messages survive.
                try:
                    line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
                except asyncio.TimeoutError:
                    if self._state != NetworkState.RUNNING:
                        break
                    continue
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
                    logger.warning(
                        "Ignored echo from peer with the same peer_id '%s' "
                        "— ensure [node] peer_id is unique per instance",
                        self._peer_id,
                    )
                    continue

                if envelope.kind == "hello":
                    self._remember_peer(source, envelope.sender_id)
                    self._remote_peer_id = envelope.sender_id
                    logger.info("Peer '%s' handshake received", envelope.sender_id)
                    continue

                self._remember_peer(source, envelope.sender_id)
                # Bounded queue: `put` blocks when full -> natural backpressure.
                await self._queue.put(envelope)
        except Exception as e:
            logger.error("Error in %s read loop: %s", source, e)
        finally:
            # The stream is gone: its peers are no longer reachable.
            for peer in self._peers_by_source.pop(source, set()):
                self._known_peers.discard(peer)
                if peer == self._remote_peer_id and peer not in self._known_peers:
                    self._remote_peer_id = None
            logger.info("%s read loop terminated", source)

    def _remember_peer(self, source: str, peer_id: str) -> None:
        self._known_peers.add(peer_id)
        self._peers_by_source.setdefault(source, set()).add(peer_id)

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

    async def send_message(self, content: str) -> str:
        """Send to the peer. If the peer is down, queue for the next reconnect.

        Returns "sent" or "queued".
        """
        if self._state != NetworkState.RUNNING:
            raise NetworkInvalidStateError("Network is not running.")

        envelope = Envelope(sender_id=self._peer_id, payload=content)

        # Outbound channel = the connector. Inbound channel = the listener.
        if self._connector is None or self._connector.stdin is None or self._connector.returncode is not None:
            if len(self._outbox) >= 200:
                # Graceful degradation: drop the oldest instead of failing hard.
                self._outbox.pop(0)
                logger.warning("Outbox full (200): dropped oldest queued message")
            self._outbox.append(envelope.to_line())
            logger.debug("Peer offline, message queued (%d in outbox)", len(self._outbox))
            return "queued"

        # Retry a previously partial flush before the new message, so ordering
        # and backlog are preserved (audit #6).
        if self._outbox:
            await self._flush_outbox()

        try:
            self._connector.stdin.write((envelope.to_line() + "\n").encode("utf-8"))
            await self._connector.stdin.drain()
            return "sent"
        except Exception as e:
            # The connector just died mid-write: queue instead of losing the text.
            self._outbox.append(envelope.to_line())
            logger.debug("Send failed (%s), message queued", e)
            return "queued"

    async def _flush_outbox(self) -> None:
        """Push queued messages out right after a successful reconnect.

        Written line by line: if the channel dies mid-flush, the unsent tail
        stays in the outbox for the next reconnect instead of vanishing.
        """
        if not self._outbox or self._connector is None or self._connector.stdin is None:
            return
        pending = list(self._outbox)
        sent = 0
        try:
            for line in pending:
                self._connector.stdin.write((line + "\n").encode("utf-8"))
                await self._connector.stdin.drain()
                sent += 1
            self._outbox.clear()
            logger.info("Flushed %d queued message(s) to peer", sent)
        except Exception as e:
            self._outbox = pending[sent:]
            logger.debug(
                "Outbox flush failed after %d message(s), %d remain queued: %s",
                sent,
                len(self._outbox),
                e,
            )

    def queued_count(self) -> int:
        return len(self._outbox)

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
        self._last_error = None

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
            # Give read loops a grace period to drain buffered lines before
            # hard cancellation.
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except asyncio.TimeoutError:
                task.cancel()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug("Network task ended: %s", e)
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
