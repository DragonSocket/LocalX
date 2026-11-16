import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.core.config import get_config
from src.core.env_validator import EnvironmentValidator
from src.core.exceptions import AppError
from src.core.history import ChatMessage, HistoryManager, Role
from src.core.network import NetworkEngine
from src.ui.tui import ChatTUI, STYLE_HISTORY, STYLE_ME, STYLE_SYSTEM, STYLE_THEM

logger = logging.getLogger(__name__)

LOG_FILE = Path("logs") / "localX.log"


def _now() -> str:
    return datetime.now().astimezone().strftime("%H:%M:%S")


def _fmt(sender: str, timestamp: str, content: str) -> str:
    return f"{timestamp}  {sender}: {content}"


class Orchestrator:
    """Glues config, persistence, transport and the TUI together."""

    def __init__(self, config, history_manager: HistoryManager,
                 network_engine: NetworkEngine, tui: ChatTUI) -> None:
        self.config = config
        self.history = history_manager
        self.network = network_engine
        self.tui = tui
        self.shutdown_event = asyncio.Event()
        self._incoming_task: asyncio.Task | None = None

    # --------------------------------------------------------------- commands
    async def handle_input(self, text: str) -> None:
        """Processes user input from the TUI."""
        if text in {"/exit", "/quit", "/q"}:
            logger.info("Exit command received.")
            await self.shutdown()
            return

        if text == "/help":
            self.tui.add_system("/exit | /peers | /status | /history [n] | /help")
            return

        if text == "/status":
            online = "online" if self.network.peer_online else "offline"
            queued = self.network.queued_count()
            self.tui.add_system(
                f"peer {self.config.node.peer_id} "
                f"listen {self.config.local.host}:{self.config.local.port} "
                f"remote {self.config.remote.host}:{self.config.remote.port} "
                f"state {online}"
                + (f" ({queued} queued)" if queued else "")
            )
            return

        if text == "/peers":
            peers = ", ".join(sorted(self.network.known_peers)) or "none"
            self.tui.add_system(f"known peers: {peers}")
            return

        if text.startswith("/history"):
            parts = text.split(maxsplit=1)
            count = 20
            if len(parts) > 1:
                if not parts[1].isdigit():
                    self.tui.add_system("usage: /history [n]")
                    return
                count = min(int(parts[1]), 200)
            tail = [m async for m in self.history.load_history()][-count:]
            for msg in tail:
                style = STYLE_ME if msg.role is Role.ME else STYLE_HISTORY
                self.tui.add_message(style, _fmt(msg.role.value, msg.timestamp, msg.content))
            return

        msg = ChatMessage(role=Role.ME, timestamp=_now(), content=text)
        try:
            await self.history.append_message(msg)
        except AppError as e:
            # Own message not persisted — still show it in the transcript.
            logger.error("History write failed for outgoing message: %s", e)
            self.tui.add_system(f"history write failed: {e}")
        self.tui.add_message(STYLE_ME, _fmt("me", msg.timestamp, msg.content))

        try:
            result = await self.network.send_message(text)
            if result == "queued":
                self.tui.add_system("peer offline — message queued, sent on reconnect")
        except AppError as e:
            self.tui.add_system(f"failed to send: {e}")
        except Exception as e:  # transport hiccup should not kill the app
            logger.error("Unexpected send failure: %s", e)
            self.tui.add_system(f"failed to send: {e}")

    # -------------------------------------------------------------- incoming
    async def _process_incoming(self) -> None:
        """Consumes envelopes from the network queue and renders them."""
        try:
            async for envelope in self.network.listen():
                if self.shutdown_event.is_set():
                    break

                msg = ChatMessage(role=Role.THEM, timestamp=_now(), content=envelope.payload)
                try:
                    await self.history.append_message(msg)
                except AppError as e:
                    # Persistence failure must not kill the live transcript:
                    # keep rendering incoming messages, warn the user.
                    logger.error("History write failed for incoming message: %s", e)
                    self.tui.add_system(f"history write failed: {e}")
                self.tui.add_message(STYLE_THEM, _fmt(envelope.sender_id, msg.timestamp, msg.content))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Incoming stream error: %s", e)
            self.tui.add_system(f"incoming stream error: {e}")

    async def _error_reporter(self) -> None:
        """Relay connection problems into the transcript (once per unique error)."""
        last_reported: str | None = None
        while not self.shutdown_event.is_set():
            error = self.network.last_error
            if error and error != last_reported:
                last_reported = error
                self.tui.add_system(error)
            elif error is None:
                last_reported = None
            await asyncio.sleep(2)

    # -------------------------------------------------------------- lifecycle
    async def shutdown(self) -> None:
        if self.shutdown_event.is_set():
            return

        self.shutdown_event.set()
        logger.info("Initiating graceful shutdown...")

        await self.network.stop()
        await self.history.shutdown()

        if self._incoming_task is not None:
            self._incoming_task.cancel()

        if self.tui.app is not None and getattr(self.tui.app, "is_running", False):
            try:
                self.tui.app.exit()
            except Exception:
                pass

        logger.info("Shutdown complete.")

    async def run(self) -> None:
        self._incoming_task = asyncio.create_task(self._process_incoming())
        reporter = asyncio.create_task(self._error_reporter())

        try:
            await self.tui.run()
        except Exception as e:
            logger.error("Unhandled exception in main loop: %s", e)
        finally:
            await self.shutdown()
            reporter.cancel()
            try:
                await reporter
            except asyncio.CancelledError:
                pass
            if self._incoming_task is not None:
                self._incoming_task.cancel()
                try:
                    await self._incoming_task
                except asyncio.CancelledError:
                    pass


async def main() -> None:
    # Logs go to a file: writing to stderr would corrupt the full-screen TUI.
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        filename=str(LOG_FILE),
    )

    try:
        config = get_config()

        validator = EnvironmentValidator()
        await validator.verify_environment()

        history = HistoryManager(config.storage.history_file)
        await history.initialize()

        network = NetworkEngine()
        await network.start(config)

        tui = ChatTUI(
            status_provider=lambda: (
                network.remote_peer_id or f"{config.remote.host}:{config.remote.port}",
                network.peer_online,
            )
        )
        orchestrator = Orchestrator(config, history, network, tui)
        tui.orchestrator = orchestrator

        tui.add_system(
            f"peer '{config.node.peer_id}' listening on "
            f"{config.local.host}:{config.local.port}, "
            f"connecting to {config.remote.host}:{config.remote.port} "
            f"(PageUp/PageDown to scroll, /help for commands)"
        )

        for msg in [m async for m in history.load_history()][-200:]:
            style = STYLE_ME if msg.role is Role.ME else STYLE_HISTORY
            tui.add_message(style, _fmt(msg.role.value, msg.timestamp, msg.content))

        await orchestrator.run()

    except AppError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
