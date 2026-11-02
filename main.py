import asyncio
import logging
import sys
from src.ui import ChatApp, SetupSubmitted, MessageSent, ChatScreen
from src.network import NcatManager
from src.database import SqliteStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatController:
    def __init__(self, app: ChatApp):
        self.app = app
        self.transport: NcatManager | None = None
        self.storage: SqliteStorage | None = None
        self.username: str = ""

    async def start_session(self, ip: str, port: int, username: str):
        self.username = username
        self.storage = SqliteStorage(f"chat_{username}.db")
        await self.storage.init()

        if ip == "0.0.0.0" or ip == "localhost":
            cmd = ["ncat", "-l", str(port)]
            logger.info(f"Starting server on port {port}")
        else:
            cmd = ["ncat", ip, str(port)]
            logger.info(f"Connecting to {ip}:{port}")

        self.transport = NcatManager(cmd)
        await self.transport.start()

        # Загружаем историю
        history = await self.storage.get_history(limit=50)
        
        # Ждем, пока UI переключится на ChatScreen
        for _ in range(20):
            if isinstance(self.app.screen, ChatScreen):
                break
            await asyncio.sleep(0.2)
        
        if isinstance(self.app.screen, ChatScreen):
            for msg in reversed(history):
                self.app.screen.add_message_to_log(msg["username"], msg["message"], is_me=(msg["username"] == self.username))
            
            # Запускаем цикл прослушивания в фоне
            asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        if not self.transport:
            return
        try:
            async for message in self.transport.stream():
                await self.storage.add_message("Peer", message)
                if isinstance(self.app.screen, ChatScreen):
                    self.app.screen.add_message_to_log("Peer", message, is_me=False)
        except Exception as e:
            logger.error(f"Listen loop error: {e}")
        finally:
            logger.info("Listen loop stopped.")

    async def handle_message_sent(self, message: str):
        if not self.transport or not self.storage:
            return
        try:
            await self.transport.send(message)
            await self.storage.add_message(self.username, message)
            if isinstance(self.app.screen, ChatScreen):
                self.app.screen.add_message_to_log(self.username, message, is_me=True)
        except Exception as e:
            logger.error(f"Error handling sent message: {e}")

    async def shutdown(self):
        if self.transport:
            await self.transport.close()
        if self.storage:
            await self.storage.close()

class ChatAppIntegrated(ChatApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller: ChatController | None = None

    async def on_setup_submitted(self, event: SetupSubmitted) -> None:
        # 1. Выполняем стандартное поведение ChatApp (переход на экран)
        super().on_setup_submitted(event)
        
        # 2. Инициализируем контроллер, если он еще не создан
        if self.controller is None:
            self.controller = ChatController(self)
        
        # 3. Запускаем сессию
        await self.controller.start_session(event.ip, event.port, event.username)

    async def on_message_sent(self, event: MessageSent) -> None:
        # Перехватываем событие и передаем в контроллер
        if self.controller:
            await self.controller.handle_message_sent(event.message)

    async def on_exit(self) -> None:
        # Гарантируем корректное завершение при выходе из приложения
        if self.controller:
            await self.controller.shutdown()

def main():
    app = ChatAppIntegrated()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
