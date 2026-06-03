# Git rules

## Commit messages
- Keep messages short and descriptive. No multi-sentence bodies unless the change
  is genuinely complex and the user requests it.
- Always ask the user for the commit message — do not auto-generate one. Wait for
  explicit input before committing.

## Branching (near-term)
- All work happens on feature branches, never directly on `main`.
- Branch naming: `<type>/<short-description>` — e.g. `feat/gemini-provider`,
  `fix/404-on-missing-ambience`, `chore/openapi-regen`.
- Open a PR to merge into `main`; do not push directly to `main`.
- Ask the user before creating, switching, or deleting branches.

## General
- Stage specific files by name — never `git add .` or `git add -A`.
- Ask before pushing, force-pushing, or resetting. Never use `--no-verify`.
