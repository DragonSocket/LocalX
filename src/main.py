import asyncio
from src.ui.chat_app import ChatApp
from src.ui.setup_screen import SetupSubmitted
from src.ui.chat_screen import ChatScreen
from src.storage.sqlite import SqliteStorage
from src.transport.ncat import NcatTransport
from src.controller.core import ChatController

class VEGAChatApp(ChatApp):
    """
    Custom ChatApp implementation that wires up components
    once the user provides configuration via SetupScreen.
    """

    async def on_setup_submitted(self, message: SetupSubmitted) -> None:
        """
        Handle SetupSubmitted message by performing Dependency Injection:
        1. Create Transport with user-provided host/port.
        2. Create Controller with injected Transport and Storage.
        3. Push ChatScreen with all dependencies.
        """
        host = message.host
        port = message.port

        # 1. Instantiate Transport (Implementation)
        transport = NcatTransport(host, port)

        # 2. Instantiate Controller (Orchestration) with injected dependencies
        controller = ChatController(
            name="VEGA",
            host=host,
            port=port,
            storage=self.storage,
            transport=transport
        )

        # 3. Inject Transport into App so it can manage lifecycle
        self.transport = transport
        self._current_host = host
        self._current_port = port

        # 4. Push ChatScreen (View) with injected Controller
        chat_screen = ChatScreen(
            transport=self.transport,
            storage=self.storage,
            controller=controller
        )
        self.push_screen(chat_screen)

def main():
    """Entry point: Composition Root."""
    # 1. Initialize Storage (Layer 2)
    storage = SqliteStorage("chat_history.db")

    # 2. Initialize App (Layer 3) with injected Storage
    # Transport is left as None, to be injected after SetupScreen.
    app = VEGAChatApp(storage=storage)

    # 3. Run the Application
    app.run()

if __name__ == "__main__":
    main()
