# Developer Instructions

You are working on the VEGA-CHAT project. You MUST follow these strict rules:

## 1. Methodology: TDD (Test-Driven Development)
For every module, you must follow this cycle:
1.  **Identify Task:** Pick a task from `TASKS.md`.
2.  **[TEST] Phase:** Write a test that defines the expected behavior. Run it. It MUST fail.
3.  **[DEV] Phase:** Write the minimum code required to make the test pass.
4.  **Verify:** Run the test again. If it passes, move to the next task.
5.  **Refactor:** Clean up the code while ensuring tests still pass.

## 2. Technical Constraints
- **Language:** Python 3.12+.
- **Package Manager:** `uv` (Always use `uv run`).
- **No Rust.**
- **Modularity:** Never import implementation classes (e.g., `NcatTransport`) into other modules. Always use `Protocols` and inject dependencies.

## 3. Workflow
- Read `SPEC.md` to understand the architectural boundaries.
- Read `TASKS.md` to see current progress.
- Update `TASKS.md` after every task completion.
