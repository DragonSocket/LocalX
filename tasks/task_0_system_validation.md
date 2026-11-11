# Task 0: System Environment Validation

## Description
Implement an `EnvironmentValidator` module to ensure the host system and Python environment meet the application's binary, library, and version requirements. This module is responsible for the initial audit during the bootstrap phase.

## Requirements
1. **Versioned Binary Verification**:
    - Use `shutil.which` to locate `ncat`.
    - Execute `ncat --version` to parse and validate the version. The application requires `ncat` version `7.0` or higher.
2. **Library Dependency Verification**:
    - Use `importlib.util.find_spec` to verify the availability of the `portalocker` library.
3. **Audit Log & Observability**:
    - Implement structured logging for every check (e.g., `[INFO] ncat detected: version 7.9 (OK)`, `[ERROR] portalocker not found in sys.path`).
4. **Error Handling & Exception Hierarchy**:
    - Define a base `AppError(Exception)` class.
    - `SystemDependencyError` must inherit from `AppError` and provide specific details about the missing/incompatible dependency.
5. **Testability**:
    - The module must be designed for high testability, allowing system calls (like `subprocess.run` or `importlib`) to be easily mocked in unit tests.
6. **Interface**:
    - Provide an entry point `verify_environment() -> None`.
7. **Integration**:
    - This module must be invoked during the application's bootstrap phase, immediately after `ConfigLoader.get_config()`.
