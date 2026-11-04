# TASK: Decompose Monolithic Files into Modular Components

## CONTEXT
The current project contains several "monolithic" files where multiple logical entities (classes, protocols, or business logic blocks) are grouped together. This violates our "One File = One Responsibility" principle and creates issues with LLM token limits and-import stability during the assembly phase.

To support the **[Qwen: Build Blocks] $\to$ [Gemma: Assemble]** workflow, we must move to a granular, file-based architecture.

## OBJECTIVE
Decompose existing large files into dedicated, modular files. Each file must contain exactly ONE primary logical entity.

## TARGET FILES & DECOMPOSITION PLAN

### 1. Controller Layer
**Current File:** `src/controller/core.py`
**Action:** Split into:
- `src/controller/models.py`: Contains all `@dataclass` definitions (`Message`, `PeerInfo`, `HistoryState`, `UserInfo`, `SystemState`, `StateData`).
- `src/controller/state.py`: Contains the `StateManager` class.
- `src/controller/formatter.py`: Contains the `TextFormatter` class.
- `src/controller/core.py`: Contains ONLY the `ChatController` class.

### 2. UI Layer
**Current File:** `src/ui/screens.py` (and/or `src/ui/setup_screen.py` if applicable)
**Action:** Split into:
- `src/ui/setup_screen.py`: Contains `SetupApp`.
- `src/ui/chat_screen.py`: Contains `ChatScreen`.

---

## EXECUTION RULES

1.  **Strict Responsibility:** A file should contain only the class/logic it is named after.
2.  **Import Integrity:** 
    - After splitting, you MUST update all imports in the entire project.
    - Use absolute imports: `from src.controller.models import Message` (not `from .models import ...`).
    - Ensure `src/controller/__init__.py` is updated or remains empty to avoid import conflicts.
3.  **No Logic Loss:** Ensure no helper methods, constants, or docstrings are lost during the migration.
4.  **Verification:** Every split must be verified by a successful import test:
    `python -c "from src.controller.core import ChatController; print('Success')"` (and similar for other modules).

## SUCCESS CRITERIA
- All monolithic files are removed or converted to clean orchestrators.
- The project structure is granular and follows the pattern: `[module]_[entity].py`.
- The application can still be instantiated via `main.py` without any `ModuleNotFoundError`.
