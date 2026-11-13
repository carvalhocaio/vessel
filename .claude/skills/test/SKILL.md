---
name: test
description: Writes or updates vessel tests — offline, on recorded real data and fakes that implement the Protocols. Use after implementing or changing code.
---

## Rules

- Tests never touch the network. Use recorded real data in `tests/fixtures/` (curated parquet, small raw samples of FastF1/Jolpica frames, `.ics`, `.toml`) and fakes that implement the `Protocol`s (`FakeSessionSource`, `FakeHistorySource`, `FakeSchedule`). Factories live in `tests/factories.py`, shared fixtures in `tests/conftest.py`.
- Facts are computed through the registry: `facts_for(KEYS, CalcInputs(...), params)` from `tests/factories.py`; reports are verified in tests with `verifier(StaticTables(inputs))`, and at least one test goes through `CuratedTables` on real parquet.
- Prefer fakes over `unittest.mock`; monkeypatch only the CLI factories (`build_schedule`, `build_session_store`, `build_history_store`, `utc_now`, `get_settings`).
- Clock-dependent code gets a fixed clock (`FileCache(root, clock)`, frozen `utc_now`).
- Analytics: assert real numbers from the recorded race/session (checked by hand once) plus small synthetic frames for edge cases (DNF, pit lane start, ties, missing data, minimum sample).
- Charts: render, check the preset size and the title/labels; then open the PNG yourself.
- One behavior per test; the name states the scenario. Never assert only "no exception".

## When a test fails

Find out which side is wrong. If the code is wrong (a test once caught a lap dropped by an `Int16` diff), fix the code and say so; if the expectation is wrong, fix the test and say why. Never bend a test to match a bug.

## Recording fixtures

See the `record-fixtures` skill.
