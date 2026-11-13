from datetime import datetime
from pathlib import Path

from vessel.analytics.race import RACE_FACTS
from vessel.analytics.registry import CalcInputs, compute_facts
from vessel.charts.output import save_registered_chart
from vessel.curation.schema import RaceTables
from vessel.domain import Draft, Event, Segment, SessionKind, SessionTableRef
from vessel.reports.drafts import Verifier, draft_dir, publish_draft

CAVEATS = (
    "Ritmo: mediana das voltas limpas (sem SC/VSC/bandeira vermelha, "
    "sem volta de entrada ou saída de box, sem a volta 1).",
    "Ganho de posições considera só pilotos classificados; largada do pit lane "
    "conta como último lugar do grid.",
)


def race_recap_dir(out_dir: Path, event: Event) -> Path:
    return draft_dir(out_dir, event, Segment.RACE_RECAP)


def race_ref(event: Event) -> SessionTableRef:
    return SessionTableRef(
        season=event.season,
        round=event.round,
        slug=event.slug,
        session_kind=SessionKind.RACE,
    )


def build_race_recap(
    event: Event,
    tables: RaceTables,
    directory: Path,
    *,
    handle: str,
    now: datetime,
    verify: Verifier,
) -> Draft:
    directory.mkdir(parents=True, exist_ok=True)
    refs = (race_ref(event),)
    inputs = CalcInputs(race_tables=tables)
    charts = tuple(
        save_registered_chart(key, inputs, refs, {}, (directory, name, handle))
        for key, name in (("chart.stints", "stints"), ("chart.positions", "positions"))
    )
    draft = Draft(
        segment=Segment.RACE_RECAP,
        event=event.ref,
        facts=compute_facts(RACE_FACTS, inputs, refs, {}),
        caveats=CAVEATS,
        charts=charts,
        generated_at=now,
    )
    publish_draft(draft, directory, verify)
    return draft
