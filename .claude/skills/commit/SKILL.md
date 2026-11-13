---
name: commit
description: Commits vessel changes with a Conventional Commits message in English, after the full check passes; pushes only when the user asked for it.
---

Use when the user asks to commit (or commit and push) a finished stage.

1. Run the full check and stop if anything fails:
   `uv run ruff format .; and uv run ruff check .; and uv run mypy src tests; and uv run pytest`
2. `git status --short` and `git diff --stat`. Stage explicit paths (`src tests config README.md`, recorded fixtures under `tests/fixtures/`). Never stage `data/`, `.env` or anything with credentials. Ask before staging an untracked file you did not create in this session.
3. Message:
   - first line `<type>(<optional scope>): <imperative summary>` in English, max 72 chars;
   - body as short bullets saying what changed and why (decisions, not file lists);
   - end with the attribution trailer from the session's instructions (e.g. `Co-Authored-By: ...`).
   - If staged work spans unrelated responsibilities, propose separate commits first.
4. Commit on the current branch (vessel works on `main`; do not create branches). Never use `--no-verify`.
5. Push (`git push origin main`) only when the user asked for it in this request. Report the hash and the push result.
