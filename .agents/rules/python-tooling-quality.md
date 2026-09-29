---
trigger: always_on
---

---
trigger: model_decision
description: "Apply formatting, docstring, and linter guidelines (Ruff/Black/Google style) for Python files."
---

# Python Formatting, Linting & Docstrings

## 1. Formatting & Layout
- Target line length: **88 characters** (standard Black/Ruff) or **80 characters** (if strictly adhering to Google Style).
- Indentation: 4 spaces strictly. Never use tabs.
- Clean imports: Organiser les imports en 3 sections séparées par une ligne vide (Standard library, Third-party, Local application). Ne jamais utiliser `from module import *`.

## 2. Docstrings & Documentation
- Document all public modules, classes, methods, and functions.
- Format docstrings using **Google style** (`Args:`, `Returns:`, `Raises:`):
  ```python
  def fetch_user_balance(user_id: str, include_pending: bool = False) -> float:
      """Calculates the current balance for an active account.

      Args:
          user_id: Unique account identifier.
          include_pending: Whether to include unconfirmed transactions.

      Returns:
          Total available balance.

      Raises:
          UserNotFoundError: If the account does not exist.
      """