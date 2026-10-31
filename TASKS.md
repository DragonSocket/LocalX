# TASKS.md

## Status: In Progress

### [x] Task 01: Setup & Contracts
- **Goal:** Initialize environment and define shared interfaces.
- **Sub-tasks:**
    - [x] Initialize project with \`uv\`.
    - [x] Create directory structure: \`src/\`, \`tests/\`, \`tasks/\`.
    - [x] Define \`typing.Protocol\` for \`Transport\` (methods: \`send\`, \`stream\`).
    - [x] Define \`typing.Protocol\` for \`Storage\` (methods: \`add\`, \`get_history\`, \`init\`).
    - [x] Install dependencies: \`textual\`, \`aiosqlite\`.
- **Definition of Done:** Project structure exists, \`uv\` environment is ready, and protocols are defined in \`src/interfaces.py\`.

### [ ] Task 02: Network Implementation
- **Goal:** Implement the \`Transport\` protocol using \`ncat\`.
- **Sub-tasks:**
    - [ ] Implement \`NcatManager(Transport)\`.
    - [ ] Use \`asyncio.create_subprocess_exec\`.
    - [ ] Implement state tracking (connected, disconnected, error).
    - [ ] Add unit tests using a \`MockTransport\`.
- **Definition of Done:** \`NcatManager\` can start a process, send/receive text, and handle process termination. Tests pass.

### [ ] Task 03: Database Implementation
- **Goal:** Implement the \`Storage\` protocol using SQLite.
- **Sub-tasks:**
    - [ ] Implement \`SqliteStorage(Storage)\`.
    - [ ] Use \`aiosqlite\` for async operations.
    - [ ] Implement history retrieval.
    - [ ] Add unit tests using \`:memory:\` database.
- **Definition of Done:** Data is correctly persisted and retrievable. Tests pass.

### [ ] Task 04: UI Implementation (View)
- **Goal:** Reactive TUI using Textual.
- **Sub-tasks:**
    - [ ] Create \`ChatApp(App)\`.
    - [ ] Implement \`SetupScreen\` (Inputs: IP, Port, Name).
    - [ ] Implement \`ChatScreen\` (Widgets: \`ChatLog\`, \`InputBox\`).
    - [ ] Implement event emission (e.g., \`MessageSent\` event).
    - [ ] Implement data display (e.g., \`update_log\` method).
- **Definition of Done:** UI shows screens and handles user input as events, without knowing about networking or DB.

### [ ] Task 05: Orchestration (Integration)
- **Goal:** Bind all components together.
- **Sub-tasks:**
    - [ ] Implement \`ChatController\`.
    - [ ] Wire \`Transport\` -> \`Controller\` -> \`Storage\` & \`UI\`.
    - [ ] Wire \`UI\` -> \`Controller\` -> \`Transport\` & \`Storage\`.
    - [ ] Implement \`main.py\` with Dependency Injection.
- **Definition of Done:** A functioning end-to-end chat application where messages are sent via \`ncat\`, saved to SQLite, and displayed in the TUI.
