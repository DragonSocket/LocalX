import os
import tomllib
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, IPvAnyAddress, FilePath, field_validator
from src.core.exceptions import ConfigParsingError, ConfigValidationError

class ConnectionConfig(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)

class StorageConfig(BaseModel):
    history_file: Path

    @field_validator('history_file')
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
    connection: ConnectionConfig
    storage: StorageConfig

class ConfigLoader:
    def __init__(self, config_path: str = "config.toml"):
        self.config_path = Path(config_path)
        self._config: AppConfig = None

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
        # Expected env vars: LOCALX_CONNECTION_HOST, LOCALX_CONNECTION_PORT, LOCALX_STORAGE_HISTORY_FILE
        prefix = "LOCALX_"
        
        if os.getenv(f"{prefix}CONNECTION_HOST"):
            data.setdefault("connection", {})["host"] = os.getenv(f"{prefix}CONNECTION_HOST")
        
        if os.getenv(f"{prefix}CONNECTION_PORT"):
            data.setdefault("connection", {})["port"] = int(os.getenv(f"{prefix}CONNECTION_PORT"))
            
        if os.getenv(f"{prefix}STORAGE_HISTORY_FILE"):
            data.setdefault("storage", {})["history_file"] = os.getenv(f"{prefix}STORAGE_HISTORY_FILE")
            
        return data

    def load(self) -> AppConfig:
        data = self._load_from_toml()
        data = self._apply_env_overrides(data)
        
        try:
            self._config = AppConfig(**data)
            return self._config
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation failed: {str(e)}")

# Singleton pattern
_global_config: AppConfig = None

def get_config() -> AppConfig:
    global _global_config
    if _global_config is None:
        loader = ConfigLoader()
        _global_config = loader.load()
    return _global_config
