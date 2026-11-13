import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from PIL import Image

from tests.factories import StaticTables
from vessel.analytics.circuit_history import HISTORY_EDITIONS
from vessel.analytics.registry import CalcInputs
from vessel.charts import PRESET_SIZES_PX
from vessel.curation import RaceTables, SeasonTables
from vessel.domain import (
    ChartPreset,
    CircuitHistoryRef,
    Draft,
    Event,
    Segment,
    SessionKind,
    Source,
)
from vessel.reports.circuit_preview import (
    PreviewInputs,
    build_circuit_preview,
    circuit_preview_dir,
)
from vessel.reports.race_recap import race_ref
from vessel.verify import verifier

NOW = datetime(2026, 11, 13, 17, tzinfo=UTC)
HANDLE = "1caiocarvalho"


def by_round(events: tuple[Event, ...], round_: int) -> Event:
    return next(event for event in events if event.round == round_)


def build(
    tmp_path: Path,
    events: tuple[Event, ...],
    round_: int,
    history: pd.DataFrame,
    season: SeasonTables,
    *,
    last_race: RaceTables | None = None,
) -> tuple[Path, Draft]:
    event = by_round(events, round_)
    directory = circuit_preview_dir(tmp_path, event)
    circuit = "vegas" if round_ == 21 else "madring"
    data = PreviewInputs(
        circuit=CircuitHistoryRef(
            circuit_id=circuit, before_season=2026, editions=HISTORY_EDITIONS
        ),
        history=history,
        season=season,
        last_race=(race_ref(by_round(events, 20)), last_race) if last_race else None,
    )
    inputs = CalcInputs(
        history_table=history, season_tables=season, race_tables=last_race
    )
    preview = build_circuit_preview(
        event,
        events,
        data,
        directory,
        handle=HANDLE,
        now=NOW,
        verify=verifier(StaticTables(inputs)),
    )
    return directory, preview.draft


def test_las_vegas_preview_writes_draft_and_charts(
    tmp_path: Path,
    schedule_2026: tuple[Event, ...],
    vegas_history: pd.DataFrame,
    season_2026: SeasonTables,
    race_2026_20: RaceTables,
) -> None:
    directory, draft = build(
        tmp_path,
        schedule_2026,
        21,
        vegas_history,
        season_2026,
        last_race=race_2026_20,
    )

    assert directory == tmp_path / "2026" / "21-las-vegas" / "circuit_preview"
    saved = Draft.model_validate(
        json.loads((directory / "draft.json").read_text(encoding="utf-8"))
    )
    assert saved == draft
    assert saved.segment is Segment.CIRCUIT_PREVIEW
    assert [chart.path for chart in saved.charts] == [
        "charts/winners_x.png",
        "charts/form_x.png",
    ]
    for chart in saved.charts:
        with Image.open(directory / chart.path) as image:
            assert image.size == PRESET_SIZES_PX[ChartPreset.X]
    assert saved.sources == (Source.FASTF1, Source.JOLPICA)
    assert any("poucas edições (3)" in caveat for caveat in saved.caveats)
    assert any("2026" in caveat for caveat in saved.caveats)


def test_preview_without_history_skips_winners_chart(
    tmp_path: Path,
    schedule_2026: tuple[Event, ...],
    madring_history: pd.DataFrame,
    season_2026: SeasonTables,
) -> None:
    _, draft = build(tmp_path, schedule_2026, 14, madring_history, season_2026)

    keys = {fact.key for fact in draft.facts}
    assert "circuit_first_race" in keys
    assert "circuit_last_winner" not in keys
    assert [chart.path for chart in draft.charts] == ["charts/form_x.png"]


def test_preview_provenance_snapshots_the_title_math(
    tmp_path: Path,
    schedule_2026: tuple[Event, ...],
    vegas_history: pd.DataFrame,
    season_2026: SeasonTables,
    race_2026_20: RaceTables,
) -> None:
    _, draft = build(
        tmp_path,
        schedule_2026,
        21,
        vegas_history,
        season_2026,
        last_race=race_2026_20,
    )

    decided = next(f for f in draft.facts if f.key == "championship_can_be_decided")
    assert decided.provenance.params["rounds"] == [21, 22, 23]
    assert decided.provenance.params["round"] == 21
    form_chart = next(c for c in draft.charts if c.spec_path == "charts/form.json")
    kinds = [ref.kind for ref in form_chart.provenance.inputs]
    assert kinds == ["season", "session"]
    assert form_chart.provenance.inputs[1].session_kind is SessionKind.RACE  # type: ignore[union-attr]
