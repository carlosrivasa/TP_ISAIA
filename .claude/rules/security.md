# Security rules

This is a personal MVP, but treat secrets and untrusted input seriously from day 1.

## Secrets
- **Never** hardcode API keys (Gemini), OCI credentials, or bucket names. Read from
  env/config (`app/core`). Provide `.env.example` with placeholder keys only.
- `.env` is git-ignored and **read-blocked for Claude** (see `.claude/settings.json`).
- Never echo secret values into logs, errors, commit messages, or responses.

## Input handling
- All request bodies validated by Pydantic before use. The `prompt` is untrusted
  text — it is data, never interpolated into shell/SQL/path operations.
- Local persistence: derive filenames from a server-generated id (e.g. UUID), never
  from raw user input. Guard against path traversal.

## LLM-specific (prompt injection)
- Treat the user `prompt` as untrusted. Keep system/instruction text separate from
  user content when calling the LLM. The LLM's JSON output is **validated against a
  Pydantic schema** before persisting or returning — never trust it blindly.
- Cap prompt length and output size.

## Transport & errors
- Don't leak internals: client-facing errors are sanitized problem responses, not
  stack traces. Log details server-side.
- CORS: restrict to known frontend origins (configurable), not `*`, before any
  non-local deployment.

## Dependencies
- Pin dependencies. Ask before adding a new one. Prefer well-maintained libs.
