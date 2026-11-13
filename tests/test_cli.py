import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vessel import __version__, cli
from vessel.cli import app
from vessel.domain import Event

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
