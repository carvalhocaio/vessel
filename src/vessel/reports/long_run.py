from datetime import datetime
from pathlib import Path

from vessel.analytics.long_run import (
    LONG_RUN_FACTS,
    SMALL_SAMPLE_LAPS,
    NoLongRunError,
    long_run_params,
    runs_from,
)
from vessel.analytics.registry import CalcInputs, compute_facts
from vessel.charts.output import save_registered_chart
from vessel.curation.schema import SessionTables
from vessel.domain import Draft, Event, Segment, SessionKind, SessionTableRef
from vessel.reports.drafts import Verifier, draft_dir, publish_draft

FIXED_CAVEATS = (
    "Sem correção de combustível: a carga de cada carro é desconhecida.",
    "Modo de motor e programa de cada equipe são desconhecidos.",
)


def long_run_dir(out_dir: Path, event: Event) -> Path:
    return draft_dir(out_dir, event, Segment.LONG_RUN)


def build_long_run(
    event: Event,
    kind: SessionKind,
    tables: SessionTables,
    directory: Path,
    *,
    handle: str,
    now: datetime,
    verify: Verifier,
) -> Draft:
    refs = (
        SessionTableRef(
            season=event.season, round=event.round, slug=event.slug, session_kind=kind
        ),
    )
    inputs = CalcInputs(session_tables=tables)
    params = long_run_params()
    runs = runs_from(inputs, params)
    if runs.empty:
        raise NoLongRunError("no long run with enough clean laps")
    directory.mkdir(parents=True, exist_ok=True)
    chart = save_registered_chart(
        "chart.long_run",
        inputs,
        refs,
        params | {"session_kind": kind.value},
        (directory, "long_run", handle),
    )
    short = runs.loc[runs["laps"] < SMALL_SAMPLE_LAPS, "driver"].tolist()
    caveats: tuple[str, ...] = FIXED_CAVEATS
    if short:
        caveats += (
            f"Amostra pequena (menos de {SMALL_SAMPLE_LAPS} voltas): "
            f"{', '.join(map(str, short))}.",
        )
    draft = Draft(
        segment=Segment.LONG_RUN,
        event=event.ref,
        facts=compute_facts(LONG_RUN_FACTS, inputs, refs, params),
        caveats=caveats,
        charts=(chart,),
        generated_at=now,
    )
    publish_draft(draft, directory, verify)
    return draft
