import asyncio
import logging
from typing import AsyncGenerator
from src.interfaces import Transport

logger = logging.getLogger(__name__)

class NcatManager(Transport):
    def __init__(self, command: list[str]):
        self.command = command
        self._process: asyncio.subprocess.Process | None = None
        self._is_running = False

    async def start(self) -> None:
        """Запускает ncat процесс."""
        if self._is_running:
            return

        try:
            self._process = await asyncio.create_subprocess_exec(
                *self.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._is_running = True
            logger.info(f"Ncat started with command: {' '.join(self.command)}")
        except Exception as e:
            logger.error(f"Failed to start ncat: {e}")
            raise

    async def send(self, message: str) -> None:
        """Отправляет сообщение в stdin процесса."""
        if not self._process or self._process.returncode is not None:
            raise ConnectionError("Ncat process is not running.")
        
        try:
            # Добавляем перевод строки, так как ncat ожидает завершенный ввод
            data = (message + "\n").encode()
            self._process.stdin.write(data)
            await self._process.stdin.drain()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise

    async def stream(self) -> AsyncGenerator[str, None]:
        """Потоковое чтение stdout процесса."""
        if not self._process:
            raise ConnectionError("Ncat process is not started.")

        try:
            while self._is_running:
                line = await self._process.stdout.readline()
                if not line:
                    # Если пришла пустая строка (EOF), процесс завершен
                    break
                yield line.decode().strip()
        except Exception as e:
            logger.error(f"Error streaming from ncat: {e}")
        finally:
            await self.close()

    async def close(self) -> None:
        """Корректное завершение процесса."""
        self._is_running = False
        if self._process:
            try:
                if self._process.returncode is None:
                    self._process.terminate()
                    await self._process.wait()
                logger.info("Ncat process terminated.")
            except Exception as e:
                logger.error(f"Error closing ncat: {e}")
            finally:
                self._process = None
