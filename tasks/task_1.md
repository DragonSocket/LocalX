# Task 1: Configuration Loading (P2P Mode)

## Description
Implement a `ConfigLoader` module to parse `config.toml` and provide a type-safe, immutable configuration object. The configuration must support both local listening parameters and remote connection parameters to enable P2P functionality.

## Requirements
1. **Schema Validation (via Pydantic)**:
    - `local.port`: Integer between 1 and 65535 (the port this node listens on).
    - `remote.host`: Valid IP address or hostname.
    - `remote.port`: Integer between 1 and 65535.
    - `storage.history_file`: A normalized, absolute file path. The module must validate that the target directory exists and is writable.
2. **Configuration Precedence**:
    - Implementation must support: `Environment Variables > config.toml`.
    - Example env vars: `LOCALX_LOCAL_PORT`, `LOCALX_REMOTE_HOST`, `LOCALX_REMOTE_PORT`, `LOCALX_STORAGE_HISTORY_FILE`.
3. **Error Handling**:
    - Define a base `AppError(Exception)` class.
    - Raise `ConfigParsingError` for TOML syntax errors.
    - Raise `ConfigValidationError` for schema or path-related failures.
4. **Immutability & Pattern**:
    - Return an immutable `AppConfig` object (using `pydantic.BaseModel` with `frozen=True`).
    - Provide a global singleton instance via `get_config() -> AppConfig`.
5. **Interface**:
    - `get_config() -> AppConfig` (Synchronous).
6. **Testability**:
    - Support mocking the file read process for unit testing.
