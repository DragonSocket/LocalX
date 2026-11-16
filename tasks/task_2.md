# Task 2: History Management

## Description
Implement a `HistoryManager` module to manage chat history using the JSONL (JSON Lines) format. The module will prioritize reliability and ease of use, using a thread pool for disk I/O to keep the main event loop responsive.

## Requirements
1. **Data Model**:
    - `ChatMessage` (immutable `dataclass`):
        - `role`: `Role` (Enum: `ME`, `THEM`).
        - `timestamp`: `datetime` object (stored as ISO 8601 string).
        - `content`: `str`.
        - `version`: `int` (schema version).
2. **Persistence (JSONL)**:
    - Use JSON Lines format for efficient $O(1)$ appends.
    - **Thread-Safe I/O**: All file operations must be executed within a `ThreadPoolExecutor` (via `loop.run_in_executor`).
    - **Batch Writing**: To minimize lock contention and I/O overhead, implement a mechanism to buffer messages in memory and flush them to disk in batches (e.g., every 10 messages or after a specific interval).
    - **Integrity**: Implement a "skip-on-error" policy during the initial load to ensure corrupted lines do not prevent the application from starting.
3. **Concurrency**:
    - Use file-level locking (e.g., via `portalocker`) during the batch-flush operation to ensure data integrity.
4. **Schema Evolution**:
    - Implement a migration registry. During `load_history`, messages with `version < CURRENT_VERSION` must be transformed.
5. **Interface**:
    - `async def load_history() -> List[ChatMessage]`: Loads the entire history into memory at startup for fast access.
    - `async def append_message(message: ChatMessage) -> None`: Adds a message to the in-memory buffer.
    - `async def shutdown() -> None`: Performs a final flush of the buffer and calls `executor.shutdown(wait=True)` to ensure all pending writes are completed before the application exits.
6. **Error Handling**:
    - `HistoryLoadError` and `HistoryWriteError` (both inheriting from `AppError`).
