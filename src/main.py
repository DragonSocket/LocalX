import asyncio
import logging
import sys
from datetime import datetime

from src.core.config import get_config
from src.core.env_validator import EnvironmentValidator
from src.core.exceptions import AppError
from src.core.history import ChatMessage, HistoryManager, Role
from src.core.network import Envelope, NetworkEngine, NetworkState
from src.ui.tui import ChatTUI, STYLE_HISTORY, STYLE_ME, STYLE_SYSTEM, STYLE_THEM

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().astimezone().strftime("%H:%M:%S")


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
            await self.tui.add_message(
                STYLE_SYSTEM,
                "[ SYSTEM ] /exit | /peers | /status | /history [n] | /help",
            )
            return

        if text == "/status":
            await self.tui.add_message(
                STYLE_SYSTEM,
                f"[ SYSTEM ] peer={self.config.node.peer_id} "
                f"listen={self.config.local.host}:{self.config.local.port} "
                f"remote={self.config.remote.host}:{self.config.remote.port} "
                f"state={self.network.state.value}",
            )
            return

        if text == "/peers":
            peers = ", ".join(sorted(self.network.known_peers)) or "none"
            await self.tui.add_message(STYLE_SYSTEM, f"[ SYSTEM ] known peers: {peers}")
            return

        if text.startswith("/history"):
            count = 20
            arg = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else ""
            if arg.isdigit():
                count = int(arg)
            tail = [m async for m in self.history.load_history()][-count:]
            for msg in tail:
                style = STYLE_ME if msg.role is Role.ME else STYLE_THEM
                await self.tui.add_message(style, f"[ {msg.role.value} {msg.timestamp} ] {msg.content}")
            return

        msg = ChatMessage(
            role=Role.ME,
            timestamp=_now(),
            content=text,
        )

        await self.history.append_message(msg)
        await self.tui.add_message(STYLE_ME, f"[ ME {msg.timestamp} ] {msg.content}")

        try:
            await self.network.send_message(text)
        except AppError as e:
            await self.tui.add_message(STYLE_SYSTEM, f"[ SYSTEM ] Failed to send: {e}")
        except Exception as e:  # transport hiccup should not kill the app
            logger.error("Unexpected send failure: %s", e)
            await self.tui.add_message(STYLE_SYSTEM, f"[ SYSTEM ] Failed to send: {e}")

    # -------------------------------------------------------------- incoming
    async def _process_incoming(self) -> None:
        """Consumes envelopes from the network queue and renders them."""
        try:
            async for envelope in self.network.listen():
                if self.shutdown_event.is_set():
                    break

                msg = ChatMessage(
                    role=Role.THEM,
                    timestamp=_now(),
                    content=envelope.payload,
                )
                await self.history.append_message(msg)
                await self.tui.add_message(
                    STYLE_THEM,
                    f"[ {envelope.sender_id} {msg.timestamp} ] {msg.content}",
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Incoming stream error: %s", e)
            self.tui.add_system(f"incoming stream error: {e}")

    async def _error_reporter(self) -> None:
        """Relay connection problems into the transcript."""
        last_reported: str | None = None
        while not self.shutdown_event.is_set():
            error = self.network.last_error
            if error and error != last_reported:
                last_reported = error
                self.tui.add_system(error)
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
            logger.error(f"Unhandled exception in main loop: {e}")
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
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        config = get_config()

        validator = EnvironmentValidator()
        await validator.verify_environment()

        history = HistoryManager(config.storage.history_file)
        await history.initialize()

        network = NetworkEngine()
        await network.start(config)

        tui = ChatTUI()
        orchestrator = Orchestrator(config, history, network, tui)
        tui.orchestrator = orchestrator

        tui.add_system(
            f"peer '{config.node.peer_id}' listening on "
            f"{config.local.host}:{config.local.port}, "
            f"connected to {config.remote.host}:{config.remote.port}"
        )

        async for msg in history.load_history():
            style = STYLE_ME if msg.role is Role.ME else STYLE_HISTORY
            await tui.add_message(style, f"[ {msg.role.value} {msg.timestamp} ] {msg.content}")

        await orchestrator.run()

    except AppError as e:
        logging.error(f"FATAL: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("Interrupted.")


if __name__ == "__main__":
    asyncio.run(main())
