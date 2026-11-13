import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.factories import StaticTables
from vessel.analytics.registry import CalcInputs
from vessel.curation import RaceTables
from vessel.domain import Draft, Event, Segment, SessionKind, SessionTableRef, Source
from vessel.reports.drafts import DraftVerificationError
from vessel.reports.race_recap import build_race_recap, race_recap_dir
from vessel.verify import verifier

NOW = datetime(2026, 11, 13, 17, tzinfo=UTC)
HANDLE = "1caiocarvalho"


def build(tmp_path: Path, event: Event, tables: RaceTables, served: RaceTables) -> Path:
    directory = race_recap_dir(tmp_path, event)
    build_race_recap(
        event,
        tables,
        directory,
        handle=HANDLE,
        now=NOW,
        verify=verifier(StaticTables(CalcInputs(race_tables=served))),
    )
    return directory


def test_race_recap_writes_verified_draft_and_charts(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    directory = build(tmp_path, sao_paulo, race_2026_20, race_2026_20)

    assert directory == tmp_path / "2026" / "20-sao-paulo" / "race_recap"
    saved = Draft.model_validate(
        json.loads((directory / "draft.json").read_text(encoding="utf-8"))
    )
    assert saved.schema_version == 3
    assert saved.segment is Segment.RACE_RECAP
    assert saved.event == sao_paulo.ref
    assert len(saved.facts) == 6
    assert [chart.path for chart in saved.charts] == [
        "charts/stints_x.png",
        "charts/positions_x.png",
    ]
    assert [chart.spec_path for chart in saved.charts] == [
        "charts/stints.json",
        "charts/positions.json",
    ]
    assert all((directory / chart.path).is_file() for chart in saved.charts)
    assert all((directory / chart.spec_path).is_file() for chart in saved.charts)
    assert saved.sources == (Source.FASTF1, Source.JOLPICA)
    assert not (directory / "draft.pending.json").exists()


def test_every_fact_and_chart_carries_provenance(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    directory = build(tmp_path, sao_paulo, race_2026_20, race_2026_20)

    saved = Draft.model_validate_json((directory / "draft.json").read_text("utf-8"))
    expected = SessionTableRef(
        season=2026, round=20, slug="20-sao-paulo", session_kind=SessionKind.RACE
    )
    gain = next(fact for fact in saved.facts if fact.key == "biggest_gain")
    assert gain.provenance.calculation == "race.biggest_gain"
    assert gain.provenance.inputs == (expected,)
    assert [chart.provenance.calculation for chart in saved.charts] == [
        "chart.stints",
        "chart.positions",
    ]


def test_divergent_draft_is_rejected_and_never_saved_as_valid(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    directory = race_recap_dir(tmp_path, sao_paulo)
    directory.mkdir(parents=True)
    (directory / "draft.json").write_text("{}", encoding="utf-8")
    tampered = race_2026_20.results.copy()
    tampered.loc[tampered["driver"] == "VER", "grid"] = 10

    with pytest.raises(DraftVerificationError, match="biggest_gain"):
        build(
            tmp_path,
            sao_paulo,
            race_2026_20,
            RaceTables(laps=race_2026_20.laps, results=tampered),
        )

    assert not (directory / "draft.json").exists()
    assert (directory / "draft.rejected.json").is_file()
