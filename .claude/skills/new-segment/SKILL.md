---
name: new-segment
description: Recipe for adding a vessel segment (quadro) end to end — source, curation, pure analytics, chart, report, CLI, fixtures, README. Use when the user asks for a new segment or a new stage of the roadmap.
---

The pipeline computes; the curator agent only writes. Every number in `draft.json` comes from here.

## 0. Plan first

Present the plan (files, contracts, tests) and wait for approval. List the decisions that change data semantics (windows, filters, tie-breaks, DNF handling) so the user can veto them.

## 1. Source

- Extend or add a `Protocol` in `src/vessel/sources/ports.py`; the adapter keeps the mapping in pure functions testable with recorded frames.
- FastF1 needs an F1 account since 2026 (`uv run python -m fastf1 auth f1tv --authenticate`, run by the user in a real terminal; `!` is not interactive). Missing timing raises `SourceUnavailableError`.
- Jolpica via `fastf1.ergast`: page with `get_next_result_page`, no per-driver loops.

## 2. Curation

- Dtypes dict in `curation/schema.py` + `conform()`; tables under `data/curated/<season>/<slug>/<session_kind>/` (or `history/...`).
- Cache with `fetch_frames`: `Forever` for closed seasons, `ParcFerme.after(session, settle)` for live ones.

## 3. Analytics (`src/vessel/analytics/<name>.py`)

- Pure functions; reuse `clean_laps`, `stint_summary`, `current_grid`, `driver_names`, `BRAZILIAN`.
- `<name>_facts(...) -> tuple[Fact, ...]` with stable snake_case keys, pt-BR `display` and `context`; omit a fact that cannot be computed instead of inventing a value.
- Respect `config/event_status.toml`: cancelled GPs never count; at-risk ones become caveats.

## 4. Chart (`src/vessel/charts/<name>.py`)

Follow the `chart-check` skill.

## 5. Report (`src/vessel/reports/<name>.py`)

- `draft_dir(out_dir, event, Segment.X)` and `write_draft`; caveats for every known limitation.
- Add the `Segment` value in `domain/draft.py` if new.

## 6. CLI

- New `typer` command with `--season`/`--round` and a sensible default from the agenda; print the key numbers and facts. Factories stay monkeypatchable.

## 7. Tests and docs

- `test` + `record-fixtures` skills. README section with fish examples.
- Run the real command, open every PNG, show the facts to the user, then hand over the Conventional Commit message.
