# vessel

Data pipeline for the [@1caiocarvalho](https://x.com/1caiocarvalho) profile: Formula 1 statistics turned into charts and structured drafts for X.

## Why vessel?

*Vessel* is Twenty One Pilots' 2013 album. The word means a container, something that carries things from one place to another. That's this project's job: carrying data from the track (FastF1, Jolpica, official calendars) to the tweet draft without spilling a single number along the way.

## Supported series

| Series | When | Data |
|---|---|---|
| Grid em Números | Thursday before the GP | Circuit history and recent form |
| Long Run | Friday night (Saturday on sprint weekends) | Race pace in free practice |
| Volta Rápida | Sunday after the race | Stints, positions and 3 numbers |

## Setup

```fish
uv sync
cp env.example .env
uv run vessel doctor
```

Fill in the secret iCal address of the F1 Google Calendar in `.env`.

## Weekend agenda

The FastF1 schedule gives rounds, formats and sessions; the official F1 calendar (secret iCal address in `VESSEL_ICAL_F1`) confirms or corrects session times and wins when they differ.

```fish
uv run vessel agenda                 # next GP, in America/Cuiaba time
uv run vessel agenda --round 22      # a specific round
uv run vessel agenda --json          # for the curator agent
```

## GP status

FastF1 and the official calendar only change once F1 publishes. When the news says a GP is at risk, postponed or cancelled, record it by hand in `config/event_status.toml` (versioned, one table per `[season.round]`):

```toml
[2026.22]
status = "at_risk"          # confirmed | at_risk | postponed | cancelled
note = "conflitos na região"
updated_on = 2026-11-13
# source = "https://..."    # link to the news, optional
```

Flow: saw the news → edit `config/event_status.toml` → check it:

```fish
uv run vessel status                 # GPs of the season that are not confirmed
uv run vessel agenda --round 22      # shows a ⚠ line with the note
```

Cancelled GPs are skipped by `agenda`, `race` and `long-run`. A typo in the file fails with the file name and the offending field.

## F1 sign-in

Since 2026, FastF1 needs an F1 account to download live timing (laps, stints, positions). Sign in once from a regular terminal; the token is stored by FastF1, outside the repo:

```fish
uv run python -m fastf1 auth f1tv --authenticate
uv run python -m fastf1 auth f1tv --status
```

Curated tables land in `data/curated/<season>/<slug>/<session>/` and are not reloaded once the session is in parc fermé.

## Grid em Números

Thursday thread before the GP: circuit history (last 10 editions actually raced at that circuit), recent form (last 5 races) and the championship math, from Jolpica.

```fish
uv run vessel grid --season 2026 --round 21   # Las Vegas
uv run vessel grid                            # next GP
```

History follows the circuit, not the GP name: `config/circuits.toml` maps each FastF1 location to a Jolpica `circuitId` (the 2026 Bahrain GP at Kuala Lumpur uses Sepang's history). A new venue needs one line there; a circuit with no past editions yields a "first race" fact. Points still at stake skip cancelled GPs and flag at-risk ones (see GP status). Past seasons are cached for good; the current season refreshes 24 h after each race.

Output: `data/out/<season>/<slug>/circuit_preview/`.

## Volta Rápida

Stints, lap-by-lap positions and fact candidates for the race.

```fish
uv run vessel race --season 2026 --round 20   # a specific race
uv run vessel race                            # last finished race
```

Output: `data/out/<season>/<slug>/race_recap/` (`draft.json` and charts).

## Long Run

Race pace in practice: each driver's longest run of consecutive clean laps on one stint (at least 6, laps above 107% of the stint median dropped), ranked by median, with tyre degradation per lap. FP2 by default, the Sprint on sprint weekends.

```fish
uv run vessel long-run --season 2026 --round 20   # FP2 at São Paulo
uv run vessel long-run --season 2026 --round 17   # Sprint at Singapore
uv run vessel long-run                            # current or last GP
uv run vessel long-run --round 20 --session fp3   # another session
```

Output: `data/out/<season>/<slug>/long_run/`. No fuel correction is applied; it is stated as a caveat in every draft.

## Draft contract

Each segment produces a `draft.json` that the curator agent turns into a post. Facts carry value, pt-BR display text, context and source, so the agent writes words, never numbers.

```fish
uv run vessel schema --output draft.schema.json
```

## Chart contract

Every chart is described by a `ChartSpec` (JSON) before it is drawn: the analysis decides *what* to show, renderers decide *how*. Each chart in a draft ships as `charts/<name>_<preset>.png` (matplotlib, for social posts) and `charts/<name>.json` (the spec, for the site), and `ChartRef.spec_path` points to the JSON.

Specs are a union discriminated by `kind` — `stint_bars`, `position_lines`, `ranged_dots`, `grid_timeline`, `ranked_dots` — with title, subtitle, sources, axes (label, unit, format, inverted, domain) and series (id, label, color, highlighted, points). Texts and labels come ready in pt-BR, and raw values ride along for hover.

```fish
uv run vessel schema --model chart --output chart.schema.json   # source for the site's TypeScript types
uv run vessel schema --model draft --output draft.schema.json
```

## Development

```fish
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest
```

## Sources

- [FastF1](https://github.com/theOehrly/Fast-F1): F1 sessions since 2018
- [Jolpica](https://github.com/jolpica/jolpica-f1): historical results (successor to Ergast)
- Official F1 calendar (ECAL, via Google Calendar)

Every chart ships with a footer crediting the sources used and the profile's handle.
