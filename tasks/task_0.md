# Task 0: System Environment Validation

## Description
Implement an `EnvironmentValidator` module to ensure the host system and Python environment meet the application's binary and library requirements during the bootstrap phase.

## Requirements
1. **Binary Verification**:
    - Use `asyncio.create_subprocess_exec` to locate and execute `ncat --version`.
    - Use a robust, non-fragile extraction method to identify the version number (e.g., searching for the first numeric sequence in the output) and validate that it is `7.0` or higher.
2. **Library Dependency Verification**:
    - Use `importlib.util.find_spec` to verify the availability of the `portalocker` library.
3. **Error Handling**:
    - Define a base `AppError(Exception)` class.
    - `SystemDependencyError` must inherit from `AppError` and include metadata: `dependency_name`, `detected_version` (optional), and `required_version`.
4. **Observability**:
    - Use the standard Python `logging` module. Every check must log a structured message (e.g., `[INFO] dependency_check: ncat found, version 7.9 (OK)` or `[ERROR] dependency_check: ncat version 6.0 < required 7.0`).
5. **Interface**:
    - `async def verify_environment() -> None`
6. **Testability**:
    - Design the module to allow mocking of the `asyncio` subprocess calls and `importlib` checks for unit testing.
