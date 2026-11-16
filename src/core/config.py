import os
import tomllib
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, field_validator
from src.core.exceptions import ConfigParsingError, ConfigValidationError


class NodeConfig(BaseModel):
    """Identity of this peer in the P2P network."""
    peer_id: str = Field(min_length=1, max_length=64)

    @property
    def name(self) -> str:
        return self.peer_id


class LocalConfig(BaseModel):
    """Listener endpoint: `ncat -l -k <host> <port>`."""
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)


class RemoteConfig(BaseModel):
    """Connector endpoint: `ncat <host> <port>`."""
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)


class StorageConfig(BaseModel):
    history_file: Path

    @field_validator("history_file")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        # Resolve to absolute path
        abs_path = v.resolve()
        # Check if directory exists and is writable
        parent = abs_path.parent
        if not parent.exists():
            raise ValueError(f"Directory {parent} does not exist.")
        if not os.access(parent, os.W_OK):
            raise ValueError(f"Directory {parent} is not writable.")
        return abs_path


class AppConfig(BaseModel):
    node: NodeConfig
    local: LocalConfig
    remote: RemoteConfig
    storage: StorageConfig

    model_config = {"frozen": True}


class ConfigLoader:
    def __init__(self, config_path: str = "config.toml"):
        path = Path(config_path)
        # Relative config paths fall back to the project root when run from
        # another cwd, so settings never "drift" from the repo.
        if not path.is_absolute() and not path.exists():
            root_candidate = Path(__file__).resolve().parent.parent.parent / path
            if root_candidate.exists():
                path = root_candidate
        self.config_path = path
        self._config: AppConfig | None = None

    def _load_from_toml(self) -> dict[str, Any]:
        if not self.config_path.exists():
            raise ConfigParsingError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ConfigParsingError(f"Failed to parse TOML: {str(e)}")

    def _apply_env_overrides(self, data: dict[str, Any]) -> dict[str, Any]:
        # Precedence: Environment Variables > config.toml
        # Expected env vars: LOCALX_NODE_PEER_ID, LOCALX_LOCAL_HOST, LOCALX_LOCAL_PORT,
        # LOCALX_REMOTE_HOST, LOCALX_REMOTE_PORT, LOCALX_STORAGE_HISTORY_FILE
        prefix = "LOCALX_"

        def set(section: str, key: str, value: Any) -> None:
            data.setdefault(section, {})[key] = value

        env_map = {
            "NODE_PEER_ID": ("node", "peer_id", str),
            "LOCAL_HOST": ("local", "host", str),
            "LOCAL_PORT": ("local", "port", int),
            "REMOTE_HOST": ("remote", "host", str),
            "REMOTE_PORT": ("remote", "port", int),
            "STORAGE_HISTORY_FILE": ("storage", "history_file", str),
        }

        for env_key, (section, key, cast) in env_map.items():
            raw = os.getenv(f"{prefix}{env_key}")
            if raw is not None:
                try:
                    set(section, key, cast(raw))
                except ValueError as e:
                    raise ConfigValidationError(
                        f"Invalid value for {prefix}{env_key}: {raw!r}"
                    ) from e

        return data

    def _migrate_legacy(self, data: dict[str, Any]) -> dict[str, Any]:
        """Support the old one-sided `[connection]` block transparently."""
        legacy = data.get("connection")
        if legacy and "remote" not in data:
            data["remote"] = {"host": legacy.get("host"), "port": legacy.get("port")}
            data.setdefault("local", {"host": "127.0.0.1", "port": legacy.get("port", 1234) + 1})
        return data

    def load(self) -> AppConfig:
        data = self._load_from_toml()
        data = self._migrate_legacy(data)
        data = self._apply_env_overrides(data)

        # Sensible defaults for a single-node local setup
        # Default peer_id is unique per instance (pid suffix) so two instances
        # of the same user never suppress each other as self-echo.
        data.setdefault("node", {}).setdefault(
            "peer_id", f"{os.getenv('USER', 'peer')}-{os.getpid()}"
        )
        data.setdefault("local", {}).setdefault("host", "127.0.0.1")

        try:
            self._config = AppConfig(**data)
            return self._config
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation failed: {str(e)}")


# Singleton pattern
_global_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _global_config
    if _global_config is None:
        loader = ConfigLoader()
        _global_config = loader.load()
    return _global_config
