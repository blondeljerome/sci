---
trigger: always_on
---

---
trigger: model_decision
description: "Apply strict security standards when generating, updating, or reviewing code (sanitization, auth, secrets, queries)."
---

# Google Secure Coding Standards

## 1. Secrets & Credentials
- **Zero hardcoded secrets**: Never commit API keys, tokens, passwords, or certificates.
- Retrieve sensitive configuration strictly via environment variables or secret managers (e.g., Vault, Secret Manager).
- Ensure `.gitignore` blocks `.env`, credentials, local SQLite databases, and secret stores.

## 2. Injection & Data Sanitization
- **SQL / NoSQL**: Never concatenate user input into queries. Use parameterized queries, prepared statements, or ORM parameter binding exclusively.
- **XSS & Output Encoding**: Treat all incoming user data as untrusted. Ensure template engines auto-escape output; sanitize before rendering raw HTML.
- **Path Traversal**: Validate and canonicalize file paths; never build filesystem paths directly from user input.

## 3. Deserialization & Cryptography
- Forbid unsafe deserialization functions (e.g., Python `pickle`, Java default `ObjectInputStream` on untrusted streams). Prefer JSON, Protobuf, or secure schema validators.
- Use modern cryptographic primitives (AES-GCM, Argon2/bcrypt for passwords, SHA-256/SHA-3 for hashes). Ban MD5, SHA-1, and custom cryptographic implementations.

## 4. Error Handling & Information Leakage
- Catch exceptions locally or at API boundaries without exposing stack traces, internal paths, or database schemas in HTTP responses.
- Log operational errors with context, but sanitize logs to remove PII (Personally Identifiable Information), passwords, and auth headers.