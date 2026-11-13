import json
from pathlib import Path
from typing import Annotated

import typer

from vessel import __version__
from vessel.agenda import render_agenda
from vessel.cache import FileCache
from vessel.cache.store import utc_now
from vessel.config import Settings, get_settings
from vessel.domain import Draft
from vessel.schedule import ReconciledSchedule, next_event
from vessel.sources.calendar_source import ICalCalendarSource
from vessel.sources.fastf1_schedule import FastF1ScheduleSource
from vessel.sources.ports import ScheduleSource

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
    if round_ is None:
        event = next_event(events, now)
    else:
        event = next((e for e in events if e.round == round_), None)
    if event is None:
        typer.echo("Nenhum GP encontrado.", err=True)
        raise typer.Exit(code=1)
    if as_json:
        typer.echo(event.model_dump_json(indent=2))
        return
    typer.echo(render_agenda(event, settings.tz))
