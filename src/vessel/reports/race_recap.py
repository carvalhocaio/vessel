from datetime import datetime
from pathlib import Path

from vessel.analytics.race import positions_by_lap, race_facts, stint_summary
from vessel.charts.race import position_chart, stint_chart
from vessel.curation.schema import RaceTables
from vessel.domain import Draft, Event, Segment, Source

DRAFT_FILE = "draft.json"
TIMING_SOURCES = (Source.FASTF1,)
POSITION_SOURCES = (Source.FASTF1, Source.JOLPICA)
CAVEATS = (
    "Ritmo: mediana das voltas limpas (sem SC/VSC/bandeira vermelha, "
    "sem volta de entrada ou saída de box, sem a volta 1).",
    "Ganho de posições considera só pilotos classificados; largada do pit lane "
    "conta como último lugar do grid.",
)


def race_recap_dir(out_dir: Path, event: Event) -> Path:
    return out_dir / str(event.season) / event.slug / Segment.RACE_RECAP.value


def build_race_recap(
    event: Event, tables: RaceTables, draft_dir: Path, handle: str, now: datetime
) -> Draft:
    laps, results = tables.laps, tables.results
    draft_dir.mkdir(parents=True, exist_ok=True)
    facts = race_facts(laps, results, Source.FASTF1)
    charts = (
        stint_chart(stint_summary(laps), laps, results).save(
            draft_dir, "stints", TIMING_SOURCES, handle
        ),
        position_chart(positions_by_lap(laps, results), laps, results).save(
            draft_dir, "positions", POSITION_SOURCES, handle
        ),
    )
    draft = Draft(
        segment=Segment.RACE_RECAP,
        event=event.ref,
        facts=facts,
        caveats=CAVEATS,
        charts=charts,
        generated_at=now,
    )
    (draft_dir / DRAFT_FILE).write_text(
        draft.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return draft
