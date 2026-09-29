---
trigger: always_on
---

---
trigger: model_decision
description: "Apply Google engineering standards for code cleanliness, readability, refactoring, and code review."
---

# Google Code Cleaning & Readability Standards

## 1. Simplicity & Clarity (KISS)
- **Readability first**: Write code optimized for the next engineer reading it, not just for brevity or cleverness.
- Avoid over-engineering: Implement what is required now, without speculative abstractions or premature generalizations (YAGNI).
- Keep functions and methods small, focused on a single responsibility (Single Responsibility Principle).

## 2. Dead Code & Noise Reduction
- Delete obsolete code, unused functions, dead branches, and commented-out blocks immediately. Rely on Git history instead of inline commenting.
- Remove redundant boilerplate: Avoid useless variable re-assignments or overly nested conditional ladders (use guard clauses / early returns).

## 3. Comments & Self-Documenting Code
- Prefer self-explanatory names for variables and functions over comments that merely restate the code.
- Write comments to explain **why** an atypical decision or workaround was made, not **what** the code does.
- Maintain consistent documentation for public interfaces (Docstrings, Javadoc, TSDoc) explaining parameters, return values, and expected error states.

## 4. Refactoring & Testing
- When modifying existing code, leave it cleaner than found (Boy Scout Rule).
- Avoid side effects in business logic: keep core domain functions pure and deterministic whenever feasible.
- Ensure every cleaned or refactored component is accompanied by unit tests asserting edge cases and nominal paths.