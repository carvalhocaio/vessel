import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.factories import (
    FakeSessionSource,
    StaticTables,
    load_history,
    load_race_2026_20,
)
from vessel.analytics.circuit_history import HISTORY_EDITIONS
from vessel.analytics.registry import CalcInputs
from vessel.cache import FileCache
from vessel.curation import RaceTables, SeasonTables, SessionTables
from vessel.curation.store import CuratedSessionStore
from vessel.curation.tables import CuratedTables, MissingCuratedTableError
from vessel.domain import CircuitHistoryRef, Event, SessionKind
from vessel.reports.circuit_preview import (
    PreviewInputs,
    build_circuit_preview,
    circuit_preview_dir,
)
from vessel.reports.long_run import build_long_run, long_run_dir
from vessel.reports.race_recap import build_race_recap, race_recap_dir, race_ref
from vessel.verify import same_value, verifier, verify_file

NOW = datetime(2026, 11, 13, 17, tzinfo=UTC)
HANDLE = "1caiocarvalho"


def by_round(events: tuple[Event, ...], round_: int) -> Event:
    return next(event for event in events if event.round == round_)


@pytest.fixture
def race_draft(tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables) -> Path:
    directory = race_recap_dir(tmp_path / "out", sao_paulo)
    build_race_recap(
        sao_paulo,
        race_2026_20,
        directory,
        handle=HANDLE,
        now=NOW,
        verify=verifier(StaticTables(CalcInputs(race_tables=race_2026_20))),
    )
    return directory / "draft.json"


def edit(path: Path, change: dict[str, object]) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    fact = next(f for f in document["facts"] if f["key"] == "biggest_gain")
    fact.update(change)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_race_draft_passes(race_draft: Path, race_2026_20: RaceTables) -> None:
    report = verify_file(race_draft, StaticTables(CalcInputs(race_tables=race_2026_20)))

    assert report.ok
    assert len(report.checks) == 8


def test_tampered_value_fails(race_draft: Path, race_2026_20: RaceTables) -> None:
    edit(race_draft, {"value": 20})

    report = verify_file(race_draft, StaticTables(CalcInputs(race_tables=race_2026_20)))

    assert not report.ok
    [failure] = report.failures
    assert failure.item == "biggest_gain"
    assert failure.saved == "20 · +19 posições"
    assert failure.recomputed == "19 · +19 posições"


def test_tampered_display_fails(race_draft: Path, race_2026_20: RaceTables) -> None:
    edit(race_draft, {"display": "+20 posições"})

    report = verify_file(race_draft, StaticTables(CalcInputs(race_tables=race_2026_20)))

    assert [failure.item for failure in report.failures] == ["biggest_gain"]


def test_tampered_spec_fails(race_draft: Path, race_2026_20: RaceTables) -> None:
    spec_path = race_draft.parent / "charts" / "positions.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["series"][0]["points"][-1]["position"] = 2
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    report = verify_file(race_draft, StaticTables(CalcInputs(race_tables=race_2026_20)))

    assert [failure.item for failure in report.failures] == [
        "chart charts/positions.json"
    ]


def test_missing_parquet_names_the_command(tmp_path: Path, race_draft: Path) -> None:
    with pytest.raises(MissingCuratedTableError) as error:
        verify_file(race_draft, CuratedTables(tmp_path / "empty"))

    message = str(error.value)
    assert "2026/20-sao-paulo/race/laps.parquet" in message
    assert "uv run vessel race --season 2026 --round 20" in message


def test_curated_parquet_round_trip(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    curated = tmp_path / "curated"
    store = CuratedSessionStore(FileCache(curated), FakeSessionSource(race_2026_20))
    tables = store.race(sao_paulo)
    directory = race_recap_dir(tmp_path / "out", sao_paulo)
    loader = CuratedTables(curated)

    build_race_recap(
        sao_paulo,
        tables,
        directory,
        handle=HANDLE,
        now=NOW,
        verify=verifier(loader),
    )

    assert verify_file(directory / "draft.json", loader).ok


def test_long_run_drafts_pass(
    tmp_path: Path,
    sao_paulo: Event,
    singapore: Event,
    fp2_2026_20: SessionTables,
    sprint_2026_17: SessionTables,
) -> None:
    for event, kind, tables in (
        (sao_paulo, SessionKind.PRACTICE_2, fp2_2026_20),
        (singapore, SessionKind.SPRINT, sprint_2026_17),
    ):
        loader = StaticTables(CalcInputs(session_tables=tables))
        directory = long_run_dir(tmp_path, event)
        build_long_run(
            event,
            kind,
            tables,
            directory,
            handle=HANDLE,
            now=NOW,
            verify=verifier(loader),
        )

        assert verify_file(directory / "draft.json", loader).ok


@pytest.mark.parametrize(("round_", "circuit"), [(21, "vegas"), (14, "madring")])
def test_circuit_preview_drafts_pass(
    tmp_path: Path,
    schedule_2026: tuple[Event, ...],
    season_2026: SeasonTables,
    round_: int,
    circuit: str,
) -> None:
    history = load_history(circuit)
    race_2026_20 = load_race_2026_20()
    event = by_round(schedule_2026, round_)
    loader = StaticTables(
        CalcInputs(
            history_table=history, season_tables=season_2026, race_tables=race_2026_20
        )
    )
    directory = circuit_preview_dir(tmp_path, event)
    build_circuit_preview(
        event,
        schedule_2026,
        PreviewInputs(
            circuit=CircuitHistoryRef(
                circuit_id=circuit, before_season=2026, editions=HISTORY_EDITIONS
            ),
            history=history,
            season=season_2026,
            last_race=(race_ref(by_round(schedule_2026, 20)), race_2026_20),
        ),
        directory,
        handle=HANDLE,
        now=NOW,
        verify=verifier(loader),
    )

    assert verify_file(directory / "draft.json", loader).ok


@pytest.mark.parametrize(
    ("saved", "recomputed", "expected"),
    [
        (19, 19, True),
        (19, 19.0, False),
        ("sim", "sim", True),
        (0.587, 0.587 + 1e-12, True),
        (0.587, 0.588, False),
        (True, 1, False),
        ({"a": [1.0, 2]}, {"a": [1.0 + 1e-12, 2]}, True),
    ],
)
def test_same_value_rules(saved: object, recomputed: object, expected: bool) -> None:
    assert same_value(saved, recomputed) is expected
