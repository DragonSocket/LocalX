# Task 4: TUI Interface

## Description
Implement a Text User Interface (TUI) using `prompt_toolkit` that acts as the user's primary interaction layer for the application.

## Requirements
1. **Layout**:
    - A split-screen layout:
        - **Top Area (Buffer)**: A scrollable read-only output area (using `prompt_toolkit.layout.containers.Window`) for displaying the chat history and incoming/outgoing messages.
        - **Bottom Area (Input)**: A dedicated, persistent input field (using `prompt_toolkit.layout.containers.HBuffer` or `prompt_toolkit.widgets.TextArea`) for user text entry.
        - **Status Bar**: A dedicated, non-scrolling status line at the absolute bottom of the window for displaying transient errors or system notifications.
2. **Message Rendering**:
    - Standard Messages: `[ ROLE HH:MM AM/PM ] <content>`
    - System Notifications: Displayed in the **Status Bar** in a distinct color (e.g., yellow or red).
3. **Input & Command Flow**:
    - The TUI captures the raw user string and passes it to `orchestrator.handle_input(raw_string)`.
    - Command parsing (e.g., `/exit`) is strictly handled by the `Orchestrator`.
4. **Data Flow (Communication)**:
    - The TUI must consume all messages (chat and system events) from an `asyncio.Queue` provided by the `Orchestrator`.
    - This ensures the TUI has a single, clear source of truth and no direct dependency on the `NetworkEngine`.
5. **UX Physics (Scrolling)**:
    - The buffer must implement "Smart Scrolling": New messages automatically scroll the view to the bottom **only if** the user's current scroll position is already at the end of the buffer.
6. **History Integration**:
    - Upon startup, the TUI must populate the scrollable buffer with the existing history loaded via `HistoryManager.load_history()`.
7. **Interface**:
    - `async def run_tui(orchestrator: 'Orchestrator') -> None`
