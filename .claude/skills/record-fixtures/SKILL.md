---
name: record-fixtures
description: How to record real FastF1/Jolpica data as small offline test fixtures for vessel. Use when a new segment or source needs test data.
---

1. Fetch through the real pipeline so the fixture matches production: run the CLI command (or the store) once; curated parquet lands in `data/curated/...`.
2. Copy the curated tables to `tests/fixtures/` with explicit names (`race_2026_20_laps.parquet`, `fp2_2026_20_drivers.parquet`, `history_vegas.parquet`, `season_2026_standings.parquet`).
3. For adapter tests, save a small raw sample in the source's own format (a few drivers/laps of `session.laps`, one Ergast results page) — drop columns parquet can't store or that aren't used.
4. Keep fixtures small (tens of KB) and real; never hand-edit numbers. Synthetic edge cases are built inside the test from these frames.
5. Write throwaway recording scripts in the session scratchpad, not in the repo.
6. FastF1 live timing needs the user's F1 login (token stored by FastF1; renew in a real terminal). Jolpica needs no login; respect its rate limit (FastF1's limiter already does).
7. Check the numbers against public results before freezing them into assertions (winner, pole, gaps).
