"""P2P Transport Layer using ncat."""

import asyncio
from typing import AsyncGenerator, Callable, Optional, Any
import uuid
import subprocess


class NcatTransport:
    """Transport using ncat for P2P communication via netcat."""
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._id: Optional[str] = None
        self._reader: Any = None
        self._writer: Any = None
        self._status_connected: bool = False
        
    @property
    def id(self) -> Optional[str]:
        return self._id
    
    @property
    def connected(self) -> bool:
        return self._status_connected

    async def connect(self, host: str, port: int) -> None:
        """Establish connection to peer."""
        try:
            cmd = [
                "ncat", "-u", "-w", "300", host, str(port)
            ]
            
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._status_connected = True
            self._id = self._id or f"{uuid.uuid4().hex[:8]}@{host}:{port}"
            
        except Exception as e:
            # Connection failed - reset state  
            if self._process is not None:
                self._process.kill()
                await self._process.wait()
                self._process = None
                
            self._id = None
            self._status_connected = False
            raise
    
    async def send(self, message: str) -> bool:
        """Send a message to the peer."""
        if self._writer is None or not self._status_connected:
            return False
        
        try:
            data = f"{message}\n".encode() + b"\r"
            
            if self._process.stdin and not self._process.stdin.at_eof():
                self._process.stdin.write(data)
                
                # Signal EOF to remote peer (ncat will send this on process close normally)
                # But for simple echo, we'll just let it read back
            
            return True
            
        except Exception:
            return False
    
    async def stream(self) -> AsyncGenerator[str, None]:
        """Create a stream that yields incoming messages."""
        try:
            if self._process is None or not self._status_connected:
                return
                
            while self._status_connected:
                try:
                    if self._process.stdout:
                        data = await asyncio.wait_for(
                            self._process.stdout.readline(), timeout=1.0
                        )
                        if data:
                            msg = data.decode().strip()
                            if msg:
                                yield msg
                except asyncio.TimeoutError:
                    continue
                    
        finally:
            self._status_connected = False
    
    async def close(self) -> None:
        """Close the connection gracefully."""
        try:
            if self._process is not None:
                # Signal EOF first, then terminate  
                if self._process.stdin and not self._process.stdin.at_eof():
                    self._process.stdin.close()
                
                self._process.terminate()
                try:
                    await asyncio.wait_for(
                        self._process.wait(), timeout=5.0
                    )
                except asyncio.TimeoutError:
                    self._process.kill()
                    await self._process.wait()
                
                self._process = None
            
            self._writer = None
            self._reader = None
            self._status_connected = False
            self._id = None
            
        except Exception:
            # Ensure process is cleaned up on error
            if self._process is not None and not self._process.poll():
                self._process.kill()
                await self._process.wait()

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
