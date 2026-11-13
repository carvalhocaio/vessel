import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from vessel import __version__
from vessel.agenda import render_agenda, status_line
from vessel.analytics.circuit_history import HISTORY_EDITIONS
from vessel.analytics.form import ChampionshipMath
from vessel.analytics.long_run import NoLongRunError, long_runs
from vessel.cache import FileCache
from vessel.cache.store import utc_now
from vessel.circuits import load_circuits
from vessel.config import Settings, get_settings
from vessel.curation.history import CuratedHistoryStore
from vessel.curation.store import CuratedSessionStore, MissingSessionError
from vessel.domain import Draft, Event, EventStatus, SessionKind
from vessel.event_status import EventStatusFile
from vessel.formatting import compound_name, format_lap_time, format_signed
from vessel.reports.circuit_preview import build_circuit_preview, circuit_preview_dir
from vessel.reports.long_run import build_long_run, long_run_dir
from vessel.reports.race_recap import build_race_recap, race_recap_dir
from vessel.schedule import (
    ReconciledSchedule,
    last_finished,
    last_finished_race,
    next_event,
)
from vessel.sources.calendar_source import ICalCalendarSource
from vessel.sources.fastf1_schedule import FastF1ScheduleSource
from vessel.sources.fastf1_session import FastF1SessionSource
from vessel.sources.jolpica import JolpicaSource
from vessel.sources.ports import ScheduleSource, SourceUnavailableError

FASTF1_AUTH_HINT = (
    "Sem login na F1 o FastF1 não baixa o timing; "
    "rode: uv run python -m fastf1 auth f1tv --authenticate"
)

RUN_TABLE = "{driver:<4} {team:<17} {compound:<14} {laps:>6} {median:>9} {deg:>10}"


class LongRunSession(StrEnum):
    FP1 = "fp1"
    FP2 = "fp2"
    FP3 = "fp3"
    SPRINT = "sprint"


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
    return ReconciledSchedule(
        FastF1ScheduleSource(settings.fastf1_cache_dir),
        calendar,
        EventStatusFile(settings.event_status_path),
    )


def build_session_store(settings: Settings) -> CuratedSessionStore:
    return CuratedSessionStore(
        FileCache(settings.curated_dir),
        FastF1SessionSource(settings.fastf1_cache_dir),
    )


def build_history_store(settings: Settings) -> CuratedHistoryStore:
    return CuratedHistoryStore(FileCache(settings.curated_dir), JolpicaSource())


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
def status(
    season: Annotated[int | None, typer.Option(help="Season year.")] = None,
) -> None:
    settings = get_settings()
    year = season or utc_now().astimezone(settings.tz).year
    events = build_schedule(settings).events(year)
    flagged = [event for event in events if event.status is not EventStatus.CONFIRMED]
    if not flagged:
        typer.echo(f"Todos os GPs de {year} estão confirmados.")
        return
    for event in flagged:
        typer.echo(f"rodada {event.round} · {event.name} · {status_line(event)}")


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
        tables = build_session_store(settings).race(event)
    except SourceUnavailableError as exc:
        typer.echo(f"{exc}. {FASTF1_AUTH_HINT}", err=True)
        raise typer.Exit(code=1) from exc
    draft_dir = race_recap_dir(settings.out_dir, event)
    draft = build_race_recap(event, tables, draft_dir, settings.handle, now)
    _echo_draft(event, draft_dir, draft)


@app.command("long-run")
def long_run(
    season: Annotated[int | None, typer.Option(help="Season year.")] = None,
    round_: Annotated[
        int | None,
        typer.Option("--round", help="Round number; current or last GP if omitted."),
    ] = None,
    session: Annotated[
        LongRunSession | None,
        typer.Option(help="Session to analyse; FP2 or Sprint by default."),
    ] = None,
) -> None:
    settings = get_settings()
    settings.ensure_dirs()
    now = utc_now()
    events = build_schedule(settings).events(season or now.astimezone(settings.tz).year)
    chosen = SessionKind(session.value) if session else None

    def session_of(event: Event) -> SessionKind:
        return chosen or event.long_run_session

    event = (
        last_finished(events, now, session_of)
        if round_ is None
        else _find_event(events, round_)
    )
    if event is None:
        typer.echo("Nenhum GP encontrado.", err=True)
        raise typer.Exit(code=1)
    kind = session_of(event)
    if event.session(kind) is None:
        typer.echo(f"{event.name} não tem a sessão {kind.value}.", err=True)
        raise typer.Exit(code=1)
    directory = long_run_dir(settings.out_dir, event)
    try:
        tables = build_session_store(settings).session(event, kind)
        draft = build_long_run(
            event, kind, tables, directory, handle=settings.handle, now=now
        )
    except SourceUnavailableError as exc:
        typer.echo(f"{exc}. {FASTF1_AUTH_HINT}", err=True)
        raise typer.Exit(code=1) from exc
    except NoLongRunError as exc:
        typer.echo(f"Nenhum long run válido em {kind.value}: {exc}.", err=True)
        raise typer.Exit(code=1) from exc
    _echo_runs(long_runs(tables.laps, tables.drivers))
    _echo_draft(event, directory, draft)


def _echo_runs(runs: pd.DataFrame) -> None:
    header = RUN_TABLE.format(
        driver="pil",
        team="equipe",
        compound="composto",
        laps="voltas",
        median="mediana",
        deg="degr. s/v",
    )
    typer.echo(header)
    for run in runs.to_dict("records"):
        degradation = run["degradation_s"]
        typer.echo(
            RUN_TABLE.format(
                driver=run["driver"],
                team=str(run["team"])[:17],
                compound=compound_name(str(run["compound"])),
                laps=run["laps"],
                median=format_lap_time(float(run["median_s"])),
                deg="—" if pd.isna(degradation) else format_signed(degradation, 3),
            )
        )


def _echo_draft(event: Event, directory: Path, draft: Draft) -> None:
    typer.echo(f"{event.name} · rodada {event.round}")
    typer.echo(f"draft: {directory / 'draft.json'}")
    for fact in draft.facts:
        typer.echo(f"- {fact.key}: {fact.display} — {fact.context}")


@app.command()
def grid(
    season: Annotated[int | None, typer.Option(help="Season year.")] = None,
    round_: Annotated[
        int | None, typer.Option("--round", help="Round number; next GP if omitted.")
    ] = None,
) -> None:
    settings = get_settings()
    settings.ensure_dirs()
    now = utc_now()
    events = build_schedule(settings).events(season or now.astimezone(settings.tz).year)
    event = next_event(events, now) if round_ is None else _find_event(events, round_)
    if event is None:
        typer.echo("Nenhum GP encontrado.", err=True)
        raise typer.Exit(code=1)
    circuit = load_circuits(settings.circuits_path).circuit_for(
        event, settings.circuits_path
    )
    history_store = build_history_store(settings)
    history = history_store.circuit(circuit, event.season, HISTORY_EDITIONS)
    season_tables = history_store.season(events, now)
    directory = circuit_preview_dir(settings.out_dir, event)
    preview = build_circuit_preview(
        event,
        events,
        history=history,
        season=season_tables,
        team_colors=_team_colors(settings, events, now),
        directory=directory,
        handle=settings.handle,
        now=now,
    )
    _echo_championship(preview.math)
    _echo_draft(event, directory, preview.draft)


def _team_colors(
    settings: Settings, events: tuple[Event, ...], now: datetime
) -> dict[str, str]:
    last = last_finished_race(events, now)
    if last is None:
        return {}
    try:
        tables = build_session_store(settings).race(last)
    except (SourceUnavailableError, MissingSessionError):
        return {}
    return {
        str(driver): str(color)
        for driver, color in zip(
            tables.results["driver"], tables.results["team_color"], strict=True
        )
        if pd.notna(color)
    }


def _echo_championship(math: ChampionshipMath | None) -> None:
    if math is None:
        return
    typer.echo(
        f"Campeonato: {math.leader} {math.leader_points:.0f} x "
        f"{math.runner_up} {math.runner_up_points:.0f} "
        f"(diferença {math.gap:.0f})"
    )
    at_risk = f"; em risco: {', '.join(map(str, math.at_risk))}" if math.at_risk else ""
    typer.echo(
        f"Em disputa: {math.available} pontos nas rodadas "
        f"{', '.join(map(str, math.rounds))}{at_risk}"
    )
    typer.echo(
        f"Neste GP: até {math.at_stake_here}; depois dele: {math.available_after}. "
        f"Título decidido aqui? {math.verdict}"
    )
