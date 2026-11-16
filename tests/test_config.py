"""Tests for the P2P config loader: schema, legacy migration, env overrides."""

import os
from pathlib import Path

import pytest

from src.core.config import ConfigLoader
from src.core.exceptions import ConfigParsingError, ConfigValidationError

MODERN_TOML = """
[node]
peer_id = "alpha"

[local]
host = "127.0.0.1"
port = 9101

[remote]
host = "127.0.0.1"
port = 9102

[storage]
history_file = "__TMP__/history_alpha.jsonl"
"""

LEGACY_TOML = """
[node]
peer_id = "old-node"

[connection]
host = "127.0.0.1"
port = 5555

[storage]
history_file = "__TMP__/history_old.jsonl"
"""


def _write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(content.replace("__TMP__", str(tmp_path)), encoding="utf-8")
    return path


def test_missing_file_raises(tmp_path: Path) -> None:
    loader = ConfigLoader(str(tmp_path / "nope.toml"))
    with pytest.raises(ConfigParsingError):
        loader.load()


def test_modern_schema_round_trip(tmp_path: Path) -> None:
    path = _write_config(tmp_path, MODERN_TOML)
    cfg = ConfigLoader(str(path)).load()
    assert cfg.node.peer_id == "alpha"
    assert cfg.local.port == 9101
    assert cfg.remote.port == 9102
    assert cfg.storage.history_file.exists() or cfg.storage.history_file.parent == tmp_path


def test_legacy_connection_block_is_migrated(tmp_path: Path) -> None:
    path = _write_config(tmp_path, LEGACY_TOML)
    cfg = ConfigLoader(str(path)).load()
    assert cfg.remote.host == "127.0.0.1"
    assert cfg.remote.port == 5555
    # listener gets port+1 by default so both sides can run in parallel
    assert cfg.local.port == 5556
    assert cfg.local.host == "127.0.0.1"


def test_env_overrides_win(tmp_path: Path, monkeypatch) -> None:
    path = _write_config(tmp_path, MODERN_TOML)
    monkeypatch.setenv("LOCALX_NODE_PEER_ID", "beta")
    monkeypatch.setenv("LOCALX_LOCAL_PORT", "9201")
    monkeypatch.setenv("LOCALX_REMOTE_PORT", "9202")
    cfg = ConfigLoader(str(path)).load()
    assert cfg.node.peer_id == "beta"
    assert cfg.local.port == 9201
    assert cfg.remote.port == 9202


def test_invalid_env_value_raises(tmp_path: Path, monkeypatch) -> None:
    path = _write_config(tmp_path, MODERN_TOML)
    monkeypatch.setenv("LOCALX_LOCAL_PORT", "not-a-number")
    with pytest.raises(ConfigValidationError):
        ConfigLoader(str(path)).load()


def test_invalid_port_raises(tmp_path: Path) -> None:
    path = _write_config(tmp_path, MODERN_TOML.replace("port = 9101", "port = 70000"))
    with pytest.raises(ConfigValidationError):
        ConfigLoader(str(path)).load()
