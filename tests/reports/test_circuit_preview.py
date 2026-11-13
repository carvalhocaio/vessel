import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from PIL import Image

from vessel.charts import PRESET_SIZES_PX
from vessel.curation import SeasonTables
from vessel.domain import ChartPreset, Draft, Event, Segment, Source
from vessel.reports.circuit_preview import build_circuit_preview, circuit_preview_dir

NOW = datetime(2026, 11, 13, 17, tzinfo=UTC)
HANDLE = "1caiocarvalho"
COLORS = {"VER": "#0600ef", "ANT": "#27f4d2"}


def by_round(events: tuple[Event, ...], round_: int) -> Event:
    return next(event for event in events if event.round == round_)


def build(
    tmp_path: Path,
    events: tuple[Event, ...],
    round_: int,
    history: pd.DataFrame,
    season: SeasonTables,
) -> tuple[Path, Draft]:
    event = by_round(events, round_)
    directory = circuit_preview_dir(tmp_path, event)
    preview = build_circuit_preview(
        event,
        events,
        history=history,
        season=season,
        team_colors=COLORS,
        directory=directory,
        handle=HANDLE,
        now=NOW,
    )
    return directory, preview.draft


def test_las_vegas_preview_writes_draft_and_charts(
    tmp_path: Path,
    schedule_2026: tuple[Event, ...],
    vegas_history: pd.DataFrame,
    season_2026: SeasonTables,
) -> None:
    directory, draft = build(tmp_path, schedule_2026, 21, vegas_history, season_2026)

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
