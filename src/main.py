import asyncio
import logging
import sys
from src.core.config import get_config
from src.core.env_validator import EnvironmentValidator
from src.core.history import HistoryManager, ChatMessage, Role
from src.core.network import NetworkEngine
from src.ui.tui import TUI
from src.core.exceptions import AppError

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, config, history_manager, network_engine, tui):
        self.config = config
        self.history = history_manager
        self.network = network_engine
        self.tui = tui
        self.message_queue = asyncio.Queue()
        self.shutdown_event = asyncio.Event()

    async def handle_input(self, text: str):
        """Processes user input from the TUI."""
        if text == "/exit":
            logger.info("Exit command received.")
            await self.shutdown()
            return

        # Add to history and send via network
        msg = ChatMessage(
            role=Role.ME,
            timestamp=datetime.now().astimezone().strftime("%I:%M %p"),
            content=text
        )
        
        await self.history.append_message(msg)
        await self.tui.add_message("class:me", f"[ ME {msg.timestamp} ] {msg.content}")
        
        try:
            await self.network.send_message(text)
        except Exception as e:
            await self.tui.add_message("class:error", f"[ SYSTEM ] Failed to send: {e}")

    async def _process_incoming(self):
        """Consumes messages from the network queue and handles them."""
        async for msg_text in self.network.listen():
            if self.shutdown_event.is_set():
                break
            
            # Format time
            ts = datetime.now().astimezone().strftime("%I:%M %p")
            
            # Create message and save
            msg = ChatMessage(
                role=Role.THEM,
                timestamp=ts,
                content=msg_text
            )
            await self.history.append_message(msg)
            await self.tui.add_message("class:them", f"[ THEM {ts} ] {msg.content}")

    async def _error_reporter(self):
        """Monitor for network errors and relay to TUI."""
        while not self.shutdown_event.is_set():
            # In a real app, we'd use a proper event or exception queue
            # For now, we'll check network state
            if self.network.state == NetworkState.IDLE and not self.shutdown_event.is_set():
                # This is a bit crude, but works for MVP
                pass 
            await asyncio.sleep(1)

    async def shutdown(self):
        """Graceful shutdown sequence."""
        if self.shutdown_event.is_set():
            return
        
        self.shutdown_event.set()
        logger.info("Initiating graceful shutdown...")
        
        await self.network.stop()
        await self.history.shutdown()
        
        # Signal TUI to exit
        # For prompt_toolkit, we can stop the loop
        # Note: The TUI run_async loop will naturally end if we signal it
        logger.info("Shutdown complete.")

    async def run(self):
        """The main execution loop."""
        # Start background tasks
        incoming_task = asyncio.create_task(self._process_incoming())
        
        try:
            await self.tui.run_tui(self)
        except Exception as e:
            logger.error(f"Unhandled exception in main loop: {e}")
            # In a real app, we'd report this to the status bar
        finally:
            await self.shutdown()
            incoming_task.cancel()
            try:
                await incoming_task
            except asyncio.CancelledError:
                pass

from datetime import datetime
from src.core.network import NetworkState

async def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        stream=sys.stderr
    )

    try:
        # 1. Config
        config = get_config()

        # 2. Env
        validator = EnvironmentValidator()
        await validator.verify_environment()

        # 3. History
        history = HistoryManager(config.storage.history_file)
        await history.initialize()

        # 4. Network
        network = NetworkEngine()
        await network.start(config.connection)

        # 5. TUI & Orchestration
        # Note: We create TUI AFTER network/history so it can use them
        tui = TUI(None) # Placeholder
        orchestrator = Orchestrator(config, history, network, tui)
        tui.orchestrator = orchestrator # Inject back

        # Load initial history into TUI
        async for msg in history.load_history():
            await tui.add_message("class:history", f"[ {msg.role.value} {msg.timestamp} ] {msg.content}")

        # Run
        await orchestrator.run()

    except Exception as e:
        logging.error(f"FATAL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
