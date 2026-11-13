import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.factories import FakeSessionSource
from vessel import __version__, cli
from vessel.cache import FileCache
from vessel.cli import app
from vessel.config import Settings
from vessel.curation import RaceTables
from vessel.curation.race import CuratedRaceStore
from vessel.domain import Event
from vessel.sources.ports import SourceUnavailableError

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_schema_prints_draft_contract() -> None:
    result = runner.invoke(app, ["schema"])

    assert result.exit_code == 0
    schema = json.loads(result.stdout)
    assert schema["title"] == "Draft"
    assert "facts" in schema["required"]


def test_schema_writes_to_file(tmp_path: Path) -> None:
    target = tmp_path / "draft.schema.json"

    result = runner.invoke(app, ["schema", "--output", str(target)])

    assert result.exit_code == 0
    assert json.loads(target.read_text(encoding="utf-8"))["title"] == "Draft"


class FakeSchedule:
    def __init__(self, events: tuple[Event, ...]) -> None:
        self._events = events

    def events(self, season: int) -> tuple[Event, ...]:
        return self._events


@pytest.fixture
def frozen_agenda(
    monkeypatch: pytest.MonkeyPatch, schedule_2026: tuple[Event, ...]
) -> None:
    monkeypatch.setattr(cli, "build_schedule", lambda _: FakeSchedule(schedule_2026))
    monkeypatch.setattr(cli, "utc_now", lambda: datetime(2026, 11, 13, 17, tzinfo=UTC))


@pytest.mark.usefixtures("frozen_agenda")
def test_agenda_shows_next_gp() -> None:
    result = runner.invoke(app, ["agenda"])

    assert result.exit_code == 0
    assert "Las Vegas Grand Prix · rodada 21" in result.stdout


@pytest.mark.usefixtures("frozen_agenda")
def test_agenda_by_round_as_json() -> None:
    result = runner.invoke(app, ["agenda", "--round", "22", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["name"] == "Qatar Grand Prix"


@pytest.mark.usefixtures("frozen_agenda")
def test_agenda_fails_for_unknown_round() -> None:
    result = runner.invoke(app, ["agenda", "--round", "99"])

    assert result.exit_code == 1


@pytest.fixture
def race_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    schedule_2026: tuple[Event, ...],
    race_2026_20: RaceTables,
) -> FakeSessionSource:
    source = FakeSessionSource(race_2026_20)
    settings = Settings(data_dir=tmp_path)
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "build_schedule", lambda _: FakeSchedule(schedule_2026))
    monkeypatch.setattr(
        cli,
        "build_race_store",
        lambda s: CuratedRaceStore(FileCache(s.curated_dir), source),
    )
    monkeypatch.setattr(cli, "utc_now", lambda: datetime(2026, 11, 13, 17, tzinfo=UTC))
    return source


def test_race_by_round_writes_draft(
    race_env: FakeSessionSource, tmp_path: Path
) -> None:
    result = runner.invoke(app, ["race", "--season", "2026", "--round", "20"])

    assert result.exit_code == 0, result.output
    assert "São Paulo Grand Prix · rodada 20" in result.stdout
    assert "biggest_gain: +19 posições" in result.stdout
    draft = tmp_path / "out" / "2026" / "20-sao-paulo" / "race_recap" / "draft.json"
    assert json.loads(draft.read_text(encoding="utf-8"))["segment"] == "race_recap"


def test_race_defaults_to_last_finished_race(race_env: FakeSessionSource) -> None:
    result = runner.invoke(app, ["race"])

    assert result.exit_code == 0, result.output
    assert "rodada 20" in result.stdout


def test_race_reuses_curated_tables(race_env: FakeSessionSource) -> None:
    runner.invoke(app, ["race", "--round", "20"])
    runner.invoke(app, ["race", "--round", "20"])

    assert race_env.calls == 1


def test_race_fails_for_unknown_round(race_env: FakeSessionSource) -> None:
    result = runner.invoke(app, ["race", "--round", "99"])

    assert result.exit_code == 1


def test_race_explains_missing_timing(race_env: FakeSessionSource) -> None:
    race_env.error = SourceUnavailableError("FastF1 has no lap timing")

    result = runner.invoke(app, ["race", "--round", "20"])

    assert result.exit_code == 1
    assert "fastf1 auth f1tv --authenticate" in result.output
