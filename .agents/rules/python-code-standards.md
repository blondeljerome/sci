---
trigger: always_on
---

---
trigger: model_decision
description: "Apply modern Python coding standards, strict type hinting, and architectural patterns whenever writing or refactoring Python code."
---

# Python Code Standards & Modern Idioms

## 1. Type Hints & Signatures
- Annotate **all** function signatures, class attributes, and return values using standard `typing` / built-in types (e.g., `list[str]`, `dict[str, Any]`, `int | None` instead of `Optional[int]`).
- Use `dataclasses` or `pydantic` models for structured data containers instead of plain untyped dictionaries or loose tuples.
- Prefer `Final` for constants and `Literal` for constrained sets of values.

## 2. Idiomatic & Modern Python (Python 3.10+)
- Use modern pattern matching (`match / case`) where it improves readability over deep `if / elif` ladders.
- Prefer `pathlib.Path` over `os.path`.
- Use context managers (`with`) systematically for I/O, database sessions, locks, and external client connections.
- Avoid side effects at module import time; encapsulate execution inside `if __name__ == "__main__":` blocks or entrypoint functions.

## 3. Control Flow & Error Handling
- Never use bare `except:` or catch generic `Exception` without re-raising or logging with structured context.
- Use guard clauses and early returns to avoid nested indentation levels.
- Avoid `assert` statements for runtime control flow or validation logic; raise explicit exceptions (`ValueError`, `TypeError`, domain-specific exceptions).