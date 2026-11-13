from datetime import datetime
from pathlib import Path

from vessel.analytics.race import positions_by_lap, race_facts, stint_summary
from vessel.charts.output import save_chart
from vessel.charts.specs.race import position_lines_spec, stint_bars_spec
from vessel.curation.schema import RaceTables
from vessel.domain import Draft, Event, Segment, Source
from vessel.reports.drafts import draft_dir, write_draft

CAVEATS = (
    "Ritmo: mediana das voltas limpas (sem SC/VSC/bandeira vermelha, "
    "sem volta de entrada ou saída de box, sem a volta 1).",
    "Ganho de posições considera só pilotos classificados; largada do pit lane "
    "conta como último lugar do grid.",
)


def race_recap_dir(out_dir: Path, event: Event) -> Path:
    return draft_dir(out_dir, event, Segment.RACE_RECAP)


def build_race_recap(
    event: Event, tables: RaceTables, directory: Path, handle: str, now: datetime
) -> Draft:
    laps, results = tables.laps, tables.results
    directory.mkdir(parents=True, exist_ok=True)
    facts = race_facts(laps, results, Source.FASTF1)
    charts = (
        save_chart(
            stint_bars_spec(stint_summary(laps), laps, results),
            directory,
            "stints",
            handle,
        ),
        save_chart(
            position_lines_spec(positions_by_lap(laps, results), laps, results),
            directory,
            "positions",
            handle,
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
    write_draft(draft, directory)
    return draft
