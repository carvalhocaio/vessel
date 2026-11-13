from datetime import datetime
from pathlib import Path

from vessel.analytics.long_run import (
    SMALL_SAMPLE_LAPS,
    long_run_facts,
    long_runs,
)
from vessel.charts.output import save_chart
from vessel.charts.specs.long_run import ranged_dots_spec
from vessel.curation.schema import SessionTables
from vessel.domain import Draft, Event, Segment, SessionKind, Source
from vessel.reports.drafts import draft_dir, write_draft

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
) -> Draft:
    runs = long_runs(tables.laps, tables.drivers)
    facts = long_run_facts(runs, Source.FASTF1)
    directory.mkdir(parents=True, exist_ok=True)
    chart = save_chart(ranged_dots_spec(runs, kind), directory, "long_run", handle)
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
        facts=facts,
        caveats=caveats,
        charts=(chart,),
        generated_at=now,
    )
    write_draft(draft, directory)
    return draft
