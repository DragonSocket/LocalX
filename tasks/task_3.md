# Task 3: Network Engine

## Description
Implement a `NetworkEngine` module that manages an `ncat` process using `asyncio.subprocess` for real-time, non-blocking communication.

## Requirements
1. **Configuration**:
    - The `start` method must accept a `ConnectionConfig` object (containing `host: str` and `port: int`).
2. **Process Management & Robust Supervision**:
    - Use `asyncio.create_subprocess_exec` to spawn `ncat`.
    - **Process Group Management**: Use `os.setpgrp` to spawn `ncat` in a new process group. This ensures the `NetworkEngine` can use `os.killpg` to kill the entire process group during shutdown, preventing "zombie" processes.
    - Implement an internal state machine: `IDLE`, `RUNNING`, `STOPPING`.
    - **Guaranteed Termination**: The `stop()` method must implement a rigorous teardown: sending `SIGTERM`, waiting for the process to exit, and if it fails to exit within a 3-second timeout, sending `SIGKILL`.
3. **Asynchronous I/O & Encoding**:
    - Use `asyncio.StreamReader` for reading `stdout` and `stderr`.
    - All I/O must use `UTF-8` encoding.
    - Redirect `stderr` to a dedicated logging handler to prevent pipe buffer hangs.
    - **Non-Blocking Backpressure**: Use an internal `asyncio.Queue(maxsize=500)`. If the queue is full, the listener must implement a "drop-oldest" strategy (removing the oldest message from the queue) to ensure the `ncat` process's pipe buffers never fill up, preventing the network connection from stalling.
4. **Error Handling**:
    - `NetworkConnectionError`: If `ncat` fails to startup or connection is refused.
    - `NetworkProcessError`: If the `ncat` process crashes or terminates unexpectedly.
    - `NetworkInvalidStateError`: If methods are called in an inappropriate state.
5. **Interface**:
    - `async def start(config: ConnectionConfig) -> None`
    - `async def send_message(content: str) -> None` (Writes to `ncat.stdin`).
    - `async def stop() -> None`
    - `async def listen() -> AsyncIterator[str]` (An async generator yielding incoming messages).
