import aiosqlite
import datetime
import logging
from typing import List, Dict, Any
from src.interfaces import Storage

logger = logging.getLogger(__name__)

class SqliteStorage(Storage):
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self) -> None:
        """Инициализация базы данных и таблицы."""
        try:
            self._conn = await aiosqlite.connect(self.db_path)
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)
            await self._conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def add_message(self, username: str, message: str) -> None:
        """Сохранение нового сообщения."""
        if not self._conn:
            raise ConnectionError("Database not initialized.")
        
        try:
            await self._conn.execute(
                "INSERT INTO messages (username, message) VALUES (?, ?)",
                (username, message)
            )
            await self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise

    async def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение последних сообщений."""
        if not self._conn:
            raise ConnectionError("Database not initialized.")
        
        try:
            async with self._conn.execute(
                "SELECT timestamp, username, message FROM messages ORDER BY id DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {"timestamp": row[0], "username": row[1], "message": row[2]}
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to fetch history: {e}")
            raise

    async def close(self) -> None:
        """Закрытие соединения."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed.")
