import json
from datetime import UTC, datetime
from pathlib import Path

from vessel.curation import RaceTables
from vessel.domain import Draft, Event, Segment, Source
from vessel.reports.race_recap import build_race_recap, race_recap_dir

NOW = datetime(2026, 11, 13, 17, tzinfo=UTC)


def test_race_recap_writes_draft_and_charts(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    draft_dir = race_recap_dir(tmp_path, sao_paulo)

    draft = build_race_recap(sao_paulo, race_2026_20, draft_dir, "1caiocarvalho", NOW)

    assert draft_dir == tmp_path / "2026" / "20-sao-paulo" / "race_recap"
    saved = Draft.model_validate(
        json.loads((draft_dir / "draft.json").read_text(encoding="utf-8"))
    )
    assert saved == draft
    assert saved.segment is Segment.RACE_RECAP
    assert saved.event == sao_paulo.ref
    assert len(saved.facts) == 6
    assert [chart.path for chart in saved.charts] == [
        "charts/stints_x.png",
        "charts/positions_x.png",
    ]
    assert all((draft_dir / chart.path).is_file() for chart in saved.charts)
    assert [chart.spec_path for chart in saved.charts] == [
        "charts/stints.json",
        "charts/positions.json",
    ]
    assert all((draft_dir / chart.spec_path).is_file() for chart in saved.charts)
    assert saved.sources == (Source.FASTF1, Source.JOLPICA)
