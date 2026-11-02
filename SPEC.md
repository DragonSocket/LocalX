# Technical Specification: VEGA-CHAT (P2P TUI)

## Concept
A lightweight, modular P2P chat application using `ncat` for networking and `Textual` for the TUI. No central server.

## Architecture (LEGO Principle)
The system must be built using Dependency Injection. Modules should only interact through `Protocols` defined in `src/interfaces.py`.

### 1. Transport Layer (`src/network.py`)
- **Protocol:** `Transport`
- **Methods:** `send(message: str)`, `stream() -> AsyncGenerator[str]`, `close()`.
- **Implementation:** `NcatTransport` (manages `ncat` subprocess).

### 2. Storage Layer (`src/database.py`)
- **Protocol:** `Storage`
- **Methods:** `init()`, `save(user, msg)`, `fetch_history(limit)`, `close()`.
- **Implementation:** `SqliteStorage` (async via `aiosqlite`).

### 3. View Layer (`src/ui.py`)
- **Framework:** `Textual`.
- **Screens:** `SetupScreen` (Config), `ChatScreen` (Main Chat).
- **Visual Identity (Crucial):**
    - **Error/System:** `Red`
    - **Self/Me:** `Cyan` or `Blue`
    - **Peer:** `Green`
    - **Timestamp:** `Dim/Grey`

### 4. Orchestration Layer (`src/main.py`)
- **Component:** `ChatController`.
- **Logic:** Listens to UI events $\to$ Orchestrates Transport & Storage $\to$ Updates UI.
