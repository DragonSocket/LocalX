# LocalX Chat CLI

A robust, asynchronous Text User Interface (TUI) client for `ncat`, designed for secure and efficient persistent chat sessions.

## Features

- **TUI Interface**: Full-screen terminal interface with a scrollable chat buffer and a dedicated input area.
- **Persistent History**: Automatically saves and loads chat history using a high-performance JSONL format.
- **Async-First**: Built on `asyncio` to ensure the UI remains responsive even during heavy network or disk I/O.
- **Robustness**: Handles process management (ncat) and file locking (portalocker) with a focus on avoiding deadlocks and zombie processes.
- **Configurable**: Easy setup via `config.toml`.

## Prerequisites

- **Python 3.11+**
- **ncat** (part of the Nmap project)
- **uv** (recommended for dependency management)

## Installation & Setup

1. **Clone the repository** (or navigate to the directory).

2. **Set up a virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   uv pip install pydantic portalocker prompt_toolkit
   ```

4. **Configure the connection**:
   Edit the `config.toml` file to specify the IP address and port of the remote `ncat` peer.
   ```toml
   [connection]
   host = "127.0.0.1"
   port = 1234

   [storage]
   history_file = "chat_history.jsonl"
   ```

## Running the Application

To start the chat, run the following command from the project root:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 src/main.py
```

## Usage

- **Chatting**: Simply type your message in the bottom input field and press `Enter`.
- **Commands**:
    - `/exit` — Gracefully closes the connection and exits the application.
- **Navigation**: Use your mouse or arrow keys to scroll through the chat history.

## Architecture Note

The application is split into a **Core** (logic, network, history) and a **Shell** (TUI). The Core logic is decoupled from the Terminal interface, making it easy to integrate into other environments (e.g., as a library or a background service).
