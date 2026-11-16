# Task 3: Network Engine (P2P Mode)

## Description
Implement a `NetworkEngine` module that enables Peer-to-Peer (P2P) communication using `ncat` as the transport layer. The engine must manage multiple concurrent connection streams (listening and connecting) and use a structured message protocol to ensure data integrity and peer identity.

## Requirements
1. **Dual-Mode Operation**:
    - **Listener Mode**: Spawns `ncat -l <local_port>` to accept incoming connections.
    - **Connector Mode**: Spawns `ncat <remote_host> <remote_port>` to connect to the target peer.
    - Both modes must run concurrently as separate tasks managed by a single `NetworkEngine` instance.
2. **Process Management & Robust Supervision**:
    - Use `asyncio.create_subprocess_exec` for both modes.
    - **Process Group Management**: Use `os.setpgrp` to spawn processes in a new process group. This ensures the `NetworkEngine` can use `os.killpg` to kill the entire process group during shutdown, preventing "zombie" processes.
    - Implement a robust state machine: `IDLE`, `RUNNING`, `STOPPING`.
    - Implement a rigorous teardown: `stop()` must send `SIGTERM`, wait with timeout, and then `SIGKILL` if necessary.
3. **Structured Protocol (Envelope Pattern)**:
    - All communication via `ncat` must follow a JSON-line-delimited protocol.
    - Each line must be a valid JSON object containing:
        - `sender_id`: A unique identifier for the peer.
        - `payload`: The actual message string.
    - This allows the engine to distinguish between different peer streams and recover from malformed lines.
4. **Asynchronous I/O & Backpressure**:
    - Use `asyncio.StreamReader` for reading `stdout` and `stderr`.
    - All I/O must use `UTF-8` encoding.
    - **Backpressure**: Use an `asyncio.Queue(maxsize=500)`. The engine must use `await queue.put()` to provide natural backpressure, ensuring that the network connection is not throttled by dropping data.
5. **Error Handling**:
    - `NetworkConnectionError`: If a connection attempt fails.
    - `NetworkProcessError`: If a subprocess crashes.
    - `NetworkInvalidStateError`: If methods are called in an inappropriate state.
6. **Interface**:
    - `async def start(config: AppConfig) -> None`
    - `async def send_message(content: str, target_id: Optional[str] = None) -> None`: Sends the message to the active connection (or a specific peer if `target_id` is provided).
    - `async def stop() -> None`
    - `async def listen() -> AsyncIterator[ChatMessage]`: Yields `ChatMessage` objects (containing payload and sender identity) deserialized from the JSON protocol.
