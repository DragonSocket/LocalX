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

        # Режим: если IP '0.0.0.0', запускаем сервер, иначе клиент
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
        chat_screen = self.app.screen if isinstance(self.app.screen, ChatScreen) else None
        
        # Если мы только перешли на экран чата, нужно дождаться, пока UI будет готов
        # В Textual это можно сделать через await app.run() или дождаться появления экрана
        # Но так как мы в асинхронном методе, мы можем просто подождать немного или использовать события.
        
        # Попробуем дождаться ChatScreen
        for _ in range(10):
            if isinstance(self.app.screen, ChatScreen):
                break
            await asyncio.sleep(0.5)
        
        if isinstance(self.app.screen, ChatScreen):
            for msg in reversed(history):
                self.app.screen.add_message_to_log(msg["username"], msg["message"], is_me=(msg["username"] == self.username))
            
            # Запускаем цикл прослушивания потока
            asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        if not self.transport:
            return
        try:
            async for message in self.transport.stream():
                # Сообщение от ncat. Обычно ncat просто шлет текст.
                # В нашем протоколе мы не шлем метаданные по сети, только текст.
                # Поэтому мы считаем, что сообщение пришло от кого-то другого.
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
            # 1. Отправляем по сети
            await self.transport.send(message)
            # 2. Сохраняем у себя
            await self.storage.add_message(self.username, message)
            # 3. Отображаем у себя
            if isinstance(self.app.screen, ChatScreen):
                self.app.screen.add_message_to_log(self.username, message, is_me=True)
        except Exception as e:
            logger.error(f"Error handling sent message: {e}")

    async def shutdown(self):
        if self.transport:
            await self.transport.close()
        if self.storage:
            await self.storage.close()

async def main():
    app = ChatApp()
    controller = ChatController(app)

    # Перехватываем события приложения для управления логикой
    # В Textual мы можем переопределить обработчики в самом приложении или слушать внешне.
    # Здесь мы добавим хуки прямо в app через monkeypatching или subclassing.
    
    original_on_setup_submitted = app.on_setup_submitted
    async def new_on_setup_submitted(event: SetupSubmitted):
        await original_on_setup_submitted(event)
        await controller.start_session(event.ip, event.port, event.username)
    
    app.on_setup_submitted = new_on_setup_submitted

    original_on_message_sent = app.on_message_sent
    async def new_on_message_sent(event: MessageSent):
        await original_on_message_sent(event)
        await controller.handle_message_sent(event.message)
    
    app.on_message_sent = new_on_message_sent

    try:
        await app.run()
    except KeyboardInterrupt:
        pass
    finally:
        await controller.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
