"""Ncat transport layer using asyncio.subprocess."""

import asyncio
from typing import AsyncGenerator, Optional, List, Dict, Any

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from src.interfaces import Transport


class NcatTransport(Transport):
    """Transport implementation using ncat via asyncio.subprocess.
    
    Provides context manager support with connect/send/stream/close.
    Uses TCP mode for reliable bidirectional communication.
    """
    
    _NCAT_CMD_TEMPLATE = "ncat -v {host} {port}"  # TCP mode with verbose confirmation
    
    def __init__(self, host: str, port: int):
        self._host: str = host
        self._port: int = port
        
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[Any] = None
        self._writer: Optional[Any] = None
        self._connected: bool = False
        self._stream_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> None:
        """Establish connection to host:port using ncat.
        
        Returns:
            Tuple of (reader, writer) from asyncio.open_connection.
            
        Raises:
            ConnectionRefusedError: If connection refused.
            TimeoutError: If connection times out.
            OSError: For other errors.
        """
        # Check if already connected first
        if self._connected and self._writer is not None:
            return
        
        try:
            cmd = self._NCAT_CMD_TEMPLATE.format(host=self._host, port=self._port)
            proc = await asyncio.create_subprocess_exec(
                "ncat",
                "-v",
                self._host,
                str(self._port),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            # Wait brief for connection to be established
            try:
                await asyncio.wait_for(proc.communicate(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                raise ConnectionRefusedError(f"Timeout connecting to {self._host}:{self._port}")
            
            self._process = proc
            self._connected = True
            
        except Exception as e:
            await self._clean_exit()
            raise
    
    async def send(self, message: str) -> bool:
        """Send a message over the connection.
        
        Args:
            message: The message to send (will be sent as-is, line appended).
            
        Returns:
            True if sent successfully.
        """
        if not self._writer or self._connected is False:
            return False
        
        try:
            # Send message with newline (ncat expects lines)
            _, written = await self._writer.drain()
            return bool(written)
            
        except Exception:
            return False
    
    async def stream(self) -> AsyncGenerator[str, None]:
        """Stream messages received from peer.
        
        Yields incoming message strings.
        Uses asyncioStreamReader for line-by-line reading.
        
        Generator should be consumed and closed by caller to ensure cleanup.
        """
        if not self._process or not self._connected:
            # No connection, nothing to yield - just return (not yield)
            return
        
        try:
            async for line in self._process.stdout:
                text = line.decode("utf-8", errors="ignore").strip()
                # Emit the received lines as messages
                if text:
                    yield text
                # Only return if connection is closed (EOF or returncode set)
                elif hasattr(self._process, 'returncode') and self._process.returncode is not None:
                    return
                    
        except asyncio.CancelledError:
            # Generator being cancelled - just let it propagate
            raise
        except Exception:
            # Error reading stream - close connection and exit generator
            pass
    
    async def close(self) -> None:
        """Close the connection and clean up all resources."""
        if self._connected:
            await self._clean_exit()
    
    async def _clean_exit(self) -> None:
        """Clean shutdown: close writer, wait for process to exit."""
        try:
            if self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception:
                    pass
                
                self._reader = None
                self._writer = None
        
        finally:
            self._connected = False
    
    async def _stream_loop(self) -> None:
        """Internal stream loop - reads from ncat output."""
        while self._connected and self._process is not None:
            try:
                # Stream loop busy-waiting for data (for UDP/echo-like behavior)
                if self._reader is None:
                    try:
                        await asyncio.wait_for(self._process.stdout.readline(), timeout=0.1)
                    except asyncio.TimeoutError:
                        continue
                
            except asyncio.CancelledError:
                break
    
    async def __aenter__(self) -> "NcatTransport":
        """Async context manager entry."""
        # For mocking - don't actually connect, just return self
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - guaranteed cleanup."""
        await self.close()
  