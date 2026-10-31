import unittest
import asyncio
import aiosqlite
from src.database import SqliteStorage

class TestSqliteStorage(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Используем :memory: для тестов
        self.storage = SqliteStorage(":memory:")
        await self.storage.init()

    async def asyncTearDown(self):
        await self.storage.close()

    async def test_add_and_get_history(self):
        # Добавляем сообщения
        await self.storage.add_message("Alice", "Hello!")
        await self.storage.add_message("Bob", "Hi Alice")

        # Получаем историю
        history = await self.storage.get_history(limit=10)

        self.assertEqual(len(history), 2)
        # SQLite возвращает историю в порядке DESC из-за ORDER BY DESC
        self.assertEqual(history[0]["username"], "Bob")
        self.assertEqual(history[0]["message"], "Hi Alice")
        self.assertEqual(history[1]["username"], "Alice")
        self.assertEqual(history[1]["message"], "Hello!")

    async def test_limit(self):
        for i in range(5):
            await self.storage.add_message("User", f"Msg {i}")
        
        history = await self.storage.get_history(limit=3)
        self.assertEqual(len(history), 3)

if __name__ == "__main__":
    unittest.main()
