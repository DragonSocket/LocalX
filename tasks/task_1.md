# Task 1: Configuration Loading

## Description
Implement a `ConfigLoader` module to parse `config.toml` and provide a type-safe, immutable configuration object used by the rest of the application.

## Requirements
1. **Schema Validation (via Pydantic)**:
    - `connection.ip`: Validated IPv4 or IPv6 address.
    - `connection.port`: Integer between 1 and 65535.
    - `storage.history_file`: A normalized, absolute file path. The module must validate that the target directory exists and is writable.
2. **Configuration Precedence**:
    - The loader must implement a precedence hierarchy: `Environment Variables > config.toml`.
3. **Error Handling**:
    - Define a base `AppError(Exception)` class.
    - Raise `ConfigParsingError` for TOML syntax errors.
    - Raise `ConfigValidationError` for schema or path-related failures.
4. **Immutability & Pattern**:
    - The returned configuration must be an immutable object (e.g., `pydantic.BaseModel` with `frozen=True`).
    - The module should provide a global singleton instance via `get_config() -> AppConfig`.
5. **Interface**:
    - `get_config() -> AppConfig` (Synchronous).
6. **Testability**:
    - Support mocking the file read process to test various configuration scenarios without actual files.
