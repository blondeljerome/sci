---
trigger: always_on
---

---
trigger: model_decision
description: "Apply these guidelines whenever writing, editing, or refactoring Python code."
---

# Google Python Style Guide Rules

Follow the official Google Python Style Guide (https://github.com/google/styleguide/blob/gh-pages/pyguide.md).

## Core Principles & Formatting
- **Indentation & Line Length**: 4 spaces per indentation level. Maximum line length is 80 characters.
- **Naming Conventions**:
  - `module_name`, `package_name` (lowercase, underscores if needed)
  - `ClassName`, `ExceptionName` (CapWords)
  - `function_name()`, `method_name()`, `variable_name` (lowercase_with_underscores)
  - `_internal_method()`, `_private_var` (leading underscore for non-public)
  - `GLOBAL_CONSTANT_NAME` (ALL_CAPS_WITH_UNDERSCORES)

## Imports & Structure
- Place imports at the top: standard library first, then third-party packages, then local application modules.
- Use full package imports for packages and modules (`import foo.bar`). Avoid `from module import *`.
- Type annotations: Annotate all function signatures and public interfaces with standard typing hints.

## Documentation & Docstrings
- Use Google-style docstrings (`Args:`, `Returns:`, `Raises:`).
- Document every public function, class, and method.

## Code Standards
- **Exceptions**: Never catch bare `except:`. Avoid catching `Exception` unless re-raising or at an outer boundary isolation layer.
- **Conditionals**: Do not use `assert` statements to validate runtime logic or function arguments; raise exceptions like `ValueError` instead.
- **Comprehensions**: Use list/dict/set comprehensions and generator expressions only for simple, short transformations.

