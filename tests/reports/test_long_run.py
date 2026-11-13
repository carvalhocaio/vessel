import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vessel.analytics.long_run import NoLongRunError
from vessel.curation import SessionTables
from vessel.domain import Draft, Event, Segment, SessionKind, Source
from vessel.reports.long_run import FIXED_CAVEATS, build_long_run, long_run_dir

NOW = datetime(2026, 11, 13, 17, tzinfo=UTC)
HANDLE = "1caiocarvalho"


def test_long_run_writes_draft_and_chart(
    tmp_path: Path, sao_paulo: Event, fp2_2026_20: SessionTables
) -> None:
    directory = long_run_dir(tmp_path, sao_paulo)

    draft = build_long_run(
        sao_paulo,
        SessionKind.PRACTICE_2,
        fp2_2026_20,
        directory,
        handle=HANDLE,
        now=NOW,
    )

    assert directory == tmp_path / "2026" / "20-sao-paulo" / "long_run"
    saved = Draft.model_validate(
        json.loads((directory / "draft.json").read_text(encoding="utf-8"))
    )
    assert saved == draft
    assert saved.segment is Segment.LONG_RUN
    assert saved.sources == (Source.FASTF1,)
    assert [chart.path for chart in saved.charts] == ["charts/long_run_x.png"]
    assert (directory / "charts" / "long_run_x.png").is_file()
    assert saved.caveats[: len(FIXED_CAVEATS)] == FIXED_CAVEATS
    assert "Amostra pequena" in saved.caveats[-1]
    assert "CAM" in saved.caveats[-1]


def test_sprint_long_run_report(
    tmp_path: Path, singapore: Event, sprint_2026_17: SessionTables
) -> None:
    draft = build_long_run(
        singapore,
        SessionKind.SPRINT,
        sprint_2026_17,
        long_run_dir(tmp_path, singapore),
        handle=HANDLE,
        now=NOW,
    )

    assert draft.event.round == 17
    assert "top_teams_pace_gap" in {fact.key for fact in draft.facts}


def test_report_refuses_session_without_long_runs(
    tmp_path: Path, sao_paulo: Event, fp2_2026_20: SessionTables
) -> None:
    empty = SessionTables(fp2_2026_20.laps.iloc[0:0], fp2_2026_20.drivers)

    with pytest.raises(NoLongRunError):
        build_long_run(
            sao_paulo, SessionKind.PRACTICE_2, empty, tmp_path, handle=HANDLE, now=NOW
        )
