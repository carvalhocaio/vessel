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
