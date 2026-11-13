---
name: python-conventions
description: Python conventions for vessel — typing, pydantic domain, Protocol ports, pure analytics, curated tables and the check command. Auto-loaded when editing .py files.
user-invocable: false
paths:
  - "**/*.py"
---

Apply these conventions whenever you read or write Python in vessel. CLAUDE.md wins on any conflict.

## Tooling

- Python 3.13, `uv` only (never `pip install`), ruff (line length 88), mypy strict.
- Done means this passes (fish shell):
  `uv run ruff format .; and uv run ruff check .; and uv run mypy src tests; and uv run pytest`

## Style

- No docstrings and no long comments: names explain the code.
- Type every public function; `X | None`, builtin generics; `Any` only at third-party boundaries (FastF1, Ergast frames).
- Constants in `UPPER_SNAKE_CASE`; no magic numbers (ruff `PLR2004` is on outside tests).
- Keyword-only arguments once a function passes five positional parameters (`PLR0917`).
- Synchronous code: FastF1 and the Jolpica client are blocking; do not introduce `async`.

## Domain and contracts

- Domain models are pydantic v2 with `frozen=True, extra="forbid"`.
- Datetimes are timezone-aware, UTC in the domain; `America/Cuiaba` only when presenting.
- `draft.json` (`Draft`/`Fact`/`ChartRef`) is a public contract: snake_case fields, lowercase enum values, stable fact keys. Never rename a fact key.
- Numbers shown to people go through `vessel.formatting` (`format_decimal`, `format_lap_time`, `format_signed`): pt-BR separators.

## Layers

- Sources sit behind `Protocol`s in `src/vessel/sources/ports.py`; adapters keep the mapping in pure functions (`*_from_session`, `*_from_ergast`) that tests call with recorded frames.
- Curated tables: dtypes dict + `conform()` in `curation/schema.py`; caching through `FileCache` and `fetch_frames` with an explicit freshness (`Forever`, `Ttl`, `ParcFerme.after(...)`).
- Analytics in `src/vessel/analytics/` are pure functions over DataFrames: no I/O, no clock, no network.
- Charts only via `vessel.charts.Chart` (never `pyplot`).
- Errors: domain-specific exceptions with a clear message (file + field for config errors); never `except Exception: pass`.
