import json
from pathlib import Path
from typing import Annotated

import typer

from vessel import __version__
from vessel.agenda import render_agenda
from vessel.cache import FileCache
from vessel.cache.store import utc_now
from vessel.config import Settings, get_settings
from vessel.curation.race import CuratedRaceStore
from vessel.domain import Draft, Event
from vessel.reports.race_recap import build_race_recap, race_recap_dir
from vessel.schedule import ReconciledSchedule, last_finished_race, next_event
from vessel.sources.calendar_source import ICalCalendarSource
from vessel.sources.fastf1_schedule import FastF1ScheduleSource
from vessel.sources.fastf1_session import FastF1SessionSource
from vessel.sources.ports import ScheduleSource, SourceUnavailableError

FASTF1_AUTH_HINT = (
    "Sem login na F1 o FastF1 não baixa o timing; "
    "rode: uv run python -m fastf1 auth f1tv --authenticate"
)

app = typer.Typer(no_args_is_help=True, help="Data pipeline for the F1 profile.")


@app.command()
def version() -> None:
    typer.echo(f"vessel {__version__}")


@app.command()
def doctor() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    typer.echo(f"handle:   @{settings.handle}")
    typer.echo(f"timezone: {settings.timezone}")
    typer.echo(f"data dir: {settings.data_dir.resolve()}")
    status = "ok" if settings.calendars.f1 else "missing"
    typer.echo(f"ical f1:  {status}")


@app.command()
def schema(
    output: Annotated[
        Path | None, typer.Option(help="Write the JSON Schema to a file.")
    ] = None,
) -> None:
    document = json.dumps(Draft.model_json_schema(), indent=2, ensure_ascii=False)
    if output is None:
        typer.echo(document)
        return
    output.write_text(document + "\n", encoding="utf-8")
    typer.echo(f"draft schema written to {output}")


def build_schedule(settings: Settings) -> ScheduleSource:
    url = settings.calendars.f1
    calendar = (
        ICalCalendarSource(str(url), FileCache(settings.http_cache_dir))
        if url
        else None
    )
    return ReconciledSchedule(FastF1ScheduleSource(settings.fastf1_cache_dir), calendar)


def build_race_store(settings: Settings) -> CuratedRaceStore:
    return CuratedRaceStore(
        FileCache(settings.curated_dir),
        FastF1SessionSource(settings.fastf1_cache_dir),
    )


def _find_event(events: tuple[Event, ...], round_: int) -> Event | None:
    return next((event for event in events if event.round == round_), None)


@app.command()
def agenda(
    season: Annotated[int | None, typer.Option(help="Season year.")] = None,
    round_: Annotated[
        int | None, typer.Option("--round", help="Round number; next GP if omitted.")
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print as JSON.")] = False,
) -> None:
    settings = get_settings()
    now = utc_now()
    events = build_schedule(settings).events(season or now.astimezone(settings.tz).year)
    event = next_event(events, now) if round_ is None else _find_event(events, round_)
    if event is None:
        typer.echo("Nenhum GP encontrado.", err=True)
        raise typer.Exit(code=1)
    if as_json:
        typer.echo(event.model_dump_json(indent=2))
        return
    typer.echo(render_agenda(event, settings.tz))


@app.command()
def race(
    season: Annotated[int | None, typer.Option(help="Season year.")] = None,
    round_: Annotated[
        int | None,
        typer.Option("--round", help="Round number; last finished race if omitted."),
    ] = None,
) -> None:
    settings = get_settings()
    settings.ensure_dirs()
    now = utc_now()
    events = build_schedule(settings).events(season or now.astimezone(settings.tz).year)
    event = (
        last_finished_race(events, now)
        if round_ is None
        else _find_event(events, round_)
    )
    if event is None:
        typer.echo("Nenhuma corrida encontrada.", err=True)
        raise typer.Exit(code=1)
    try:
        tables = build_race_store(settings).tables(event)
    except SourceUnavailableError as exc:
        typer.echo(f"{exc}. {FASTF1_AUTH_HINT}", err=True)
        raise typer.Exit(code=1) from exc
    draft_dir = race_recap_dir(settings.out_dir, event)
    draft = build_race_recap(event, tables, draft_dir, settings.handle, now)
    typer.echo(f"{event.name} · rodada {event.round}")
    typer.echo(f"draft: {draft_dir / 'draft.json'}")
    for fact in draft.facts:
        typer.echo(f"- {fact.key}: {fact.display} — {fact.context}")
