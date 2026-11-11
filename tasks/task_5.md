# Task 5: Application Orchestration

## Description
Implement the main application entry point and the orchestration logic that wires all components together. This module manages the high-level application lifecycle and the primary `asyncio` event loop.

## Requirements
1. **Lifecycle Management**:
    - **Startup**: Orchestrate the sequence: `ConfigLoader` $\rightarrow$ `EnvironmentValidator` $\rightarrow$ `HistoryManager` $\rightarrow$ `NetworkEngine` $\rightarrow$ `TUI`.
    - **Robust Teordown**: Implement a strict shutdown sequence. When a `SIGINT` or `/exit` command is received, the orchestrator must call `shutdown()` on all components in **reverse order** of their initialization (i.e., `TUI` $\rightarrow$ `NetworkEngine` $\rightarrow$ `HistoryManager`). This ensures the `HistoryManager` can flush its buffers and join its thread pool before the event loop is destroyed.
    - **Signal Handling**: Use `loop.add_signal_handler` (or the `asyncio` equivalent) to intercept `SIGINT` and trigger the graceful shutdown sequence.
2. **Error Reporting Strategy**:
    - **Phase 1 (Pre-TUI)**: Errors occurring during the bootstrap phase must be logged to `sys.stderr` and recorded via the `logging` module.
    - **Phase 2 (Post-TUI)**: Errors occurring during the main loop must be reported through the TUI's **Status Bar**.
3. **Dependency Injection**:
    - The orchestrator must instantiate all components and inject them into one another.
4. **Interface**:
    - `async def main() -> None`
