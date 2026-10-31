import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from src.network import NcatManager

class TestNcatManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.command = ["ncat", "-l", "1234"]
        self.manager = NcatManager(self.command)

    @patch("asyncio.create_subprocess_exec")
    async def test_start(self, mock_exec):
        mock_process = AsyncMock()
        mock_exec.return_value = mock_process
        
        await self.manager.start()
        
        mock_exec.assert_called_once_with(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.assertTrue(self.manager._is_running)

    @patch("asyncio.create_subprocess_exec")
    async def test_send(self, mock_exec):
        mock_process = AsyncMock()
        mock_process.stdin = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.returncode = None
        mock_exec.return_value = mock_process
        
        await self.manager.start()
        await self.manager.send("hello")
        
        mock_process.stdin.write.assert_called_once_with(b"hello\n")
        mock_process.stdin.drain.assert_called_once()

    @patch("asyncio.create_subprocess_exec")
    async def test_stream(self, mock_exec):
        mock_process = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[
            b"line1\n",
            b"line2\n",
            b""
        ])
        mock_process.returncode = None
        mock_exec.return_value = mock_process
        
        await self.manager.start()
        
        lines = []
        async for line in self.manager.stream():
            lines.append(line)
            
        self.assertEqual(lines, ["line1", "line2"])

    @patch("asyncio.create_subprocess_exec")
    async def test_close(self, mock_exec):
        mock_process = AsyncMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        mock_process.returncode = None
        mock_exec.return_value = mock_process
        
        await self.manager.start()
        await self.manager.close()
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once()
        self.assertFalse(self.manager._is_running)

if __name__ == "__main__":
    unittest.main()
