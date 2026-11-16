# localX — P2P ncat chat

A full-screen TUI chat where **each peer is both a server and a client**. There is no
central server: two (or more) localX instances talk directly over `ncat`.

## How the transport works

Every peer runs two `ncat` processes managed by `NetworkEngine`:

| Role      | Command                         | Purpose                              |
|-----------|---------------------------------|--------------------------------------|
| Listener  | `ncat -l -k <local.host> <local.port>` | Accepts peers, reads their messages |
| Connector | `ncat <remote.host> <remote.port>`     | Sends this peer's messages, auto-reconnects |

Either side can start first — the connector retries until the peer's listener is up.

Messages are one JSON object per line:

```json
{"sender_id": "alice", "payload": "hi", "kind": "message", "version": 1}
```

`kind` is `hello` (handshake, not shown in the transcript) or `message`.
Self-echoes are dropped: the listener broadcasts its stdin to all clients, so a
copy of an outgoing line can come back on another stream.

## Prerequisites

- Python 3.12+
- `ncat` (Nmap project), version 7.0+
- `uv`

## Install

```bash
uv venv
uv sync
```

## Configuration

`config.toml` uses four sections:

```toml
[node]
peer_id = "alice"

[local]
host = "127.0.0.1"
port = 9001

[remote]
host = "127.0.0.1"
port = 9002

[storage]
history_file = "chat_history.jsonl"
```

Environment variables override the file (useful for running two peers locally):

| Variable | Section/key |
|---|---|
| `LOCALX_NODE_PEER_ID` | `node.peer_id` |
| `LOCALX_LOCAL_HOST` | `local.host` |
| `LOCALX_LOCAL_PORT` | `local.port` |
| `LOCALX_REMOTE_HOST` | `remote.host` |
| `LOCALX_REMOTE_PORT` | `remote.port` |
| `LOCALX_STORAGE_HISTORY_FILE` | `storage.history_file` |

An old single-sided `[connection]` block is migrated to `[remote]`/`[local]`
automatically.

## Running two peers locally

```bash
# terminal 1
LOCALX_NODE_PEER_ID=alice LOCALX_LOCAL_PORT=9001 LOCALX_REMOTE_PORT=9002 \
  LOCALX_STORAGE_HISTORY_FILE=history_alice.jsonl \
  uv run python src/main.py

# terminal 2
LOCALX_NODE_PEER_ID=bob LOCALX_LOCAL_PORT=9002 LOCALX_REMOTE_PORT=9001 \
  LOCALX_STORAGE_HISTORY_FILE=history_bob.jsonl \
  uv run python src/main.py
```

Type a message in either terminal and it appears in the other one.

## Usage

- Type a message and press `Enter`.
- Commands: `/help`, `/status`, `/peers`, `/history [n]`, `/exit`
- `Ctrl+C` / `Ctrl+D` exits.

## Scrolling the transcript

| Action | Effect |
|---|---|
| `PageUp` / `PageDown` | move through history one page at a time |
| `Ctrl+Home` / `Ctrl+End` | jump to the oldest / newest line |
| mouse wheel | three lines per notch over the transcript |

Incoming messages are rendered immediately, even while scrolled up — the status
line shows `N new below` and `PageDown` returns you to the tail. Sending a
message resets the scroll offset.

## Architecture

```
src/
  main.py            orchestrator: wires config, history, network, TUI
  core/
    config.py        TOML + env loading, validation, legacy migration
    network.py       dual-mode ncat engine, reconnects, envelope protocol
    history.py       JSONL persistence with portalocker and batching
    env_validator.py startup audit of ncat and Python deps
    exceptions.py    typed error hierarchy
  ui/
    tui.py           prompt_toolkit full-screen chat surface
```

The core is decoupled from the terminal: `NetworkEngine` and `HistoryManager`
are plain async classes usable as a library or behind another frontend.
