import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from tests.factories import FIXTURES, FakeHistorySource, FakeSessionSource
from vessel import __version__, cli
from vessel.cache import FileCache
from vessel.cli import app
from vessel.config import Settings
from vessel.curation import RaceTables, SeasonTables, SessionTables
from vessel.curation.history import CuratedHistoryStore
from vessel.curation.store import CuratedSessionStore
from vessel.domain import Event, SessionKind
from vessel.event_status import EventStatusFile
from vessel.schedule import ReconciledSchedule
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
        "build_session_store",
        lambda s: CuratedSessionStore(FileCache(s.curated_dir), source),
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


@pytest.fixture
def long_run_env(
    race_env: FakeSessionSource,
    fp2_2026_20: SessionTables,
    sprint_2026_17: SessionTables,
) -> FakeSessionSource:
    race_env.sessions[SessionKind.PRACTICE_2] = fp2_2026_20
    race_env.sessions[SessionKind.SPRINT] = sprint_2026_17
    return race_env


def test_long_run_by_round_prints_table_and_writes_draft(
    long_run_env: FakeSessionSource, tmp_path: Path
) -> None:
    result = runner.invoke(app, ["long-run", "--season", "2026", "--round", "20"])

    assert result.exit_code == 0, result.output
    assert "ANT  Mercedes" in result.stdout
    assert "top_teams_pace_gap: 0,143 s/volta" in result.stdout
    draft = tmp_path / "out" / "2026" / "20-sao-paulo" / "long_run" / "draft.json"
    assert json.loads(draft.read_text(encoding="utf-8"))["segment"] == "long_run"


def test_long_run_uses_sprint_on_sprint_weekends(
    long_run_env: FakeSessionSource,
) -> None:
    result = runner.invoke(app, ["long-run", "--round", "17"])

    assert result.exit_code == 0, result.output
    assert "Singapore Grand Prix · rodada 17" in result.stdout
    assert "intermediário" in result.stdout


def test_long_run_defaults_to_last_finished_session(
    long_run_env: FakeSessionSource,
) -> None:
    result = runner.invoke(app, ["long-run"])

    assert result.exit_code == 0, result.output
    assert "rodada 20" in result.stdout


def test_long_run_session_option_overrides_default(
    long_run_env: FakeSessionSource,
) -> None:
    result = runner.invoke(app, ["long-run", "--session", "sprint"])

    assert result.exit_code == 0, result.output
    assert "rodada 17" in result.stdout


def test_long_run_rejects_session_missing_from_weekend(
    long_run_env: FakeSessionSource,
) -> None:
    result = runner.invoke(app, ["long-run", "--round", "17", "--session", "fp2"])

    assert result.exit_code == 1
    assert "não tem a sessão fp2" in result.output


def test_long_run_reports_sessions_without_long_runs(
    long_run_env: FakeSessionSource, fp2_2026_20: SessionTables
) -> None:
    long_run_env.sessions[SessionKind.PRACTICE_2] = SessionTables(
        fp2_2026_20.laps.iloc[0:0], fp2_2026_20.drivers
    )

    result = runner.invoke(app, ["long-run", "--round", "20"])

    assert result.exit_code == 1
    assert "Nenhum long run válido" in result.output


@pytest.fixture
def status_agenda(
    monkeypatch: pytest.MonkeyPatch, schedule_2026: tuple[Event, ...]
) -> None:
    schedule = ReconciledSchedule(
        FakeSchedule(schedule_2026),
        None,
        EventStatusFile(FIXTURES / "event_status.toml"),
    )
    monkeypatch.setattr(cli, "build_schedule", lambda _: schedule)
    monkeypatch.setattr(cli, "utc_now", lambda: datetime(2026, 11, 13, 17, tzinfo=UTC))


@pytest.mark.usefixtures("status_agenda")
def test_agenda_json_includes_status() -> None:
    result = runner.invoke(app, ["agenda", "--round", "22", "--json"])

    assert result.exit_code == 0, result.output
    event = json.loads(result.stdout)
    assert event["status"] == "at_risk"
    assert event["notice"]["note"] == "conflitos na região"


@pytest.mark.usefixtures("status_agenda")
def test_agenda_skips_cancelled_next_gp() -> None:
    result = runner.invoke(app, ["agenda"])

    assert result.exit_code == 0, result.output
    assert "Qatar Grand Prix · rodada 22" in result.stdout
    assert "⚠ Em risco: conflitos na região (atualizado em 13/11)" in result.stdout


@pytest.mark.usefixtures("status_agenda")
def test_status_lists_flagged_gps() -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    assert lines[0].startswith("rodada 21 · Las Vegas Grand Prix · ⚠ Cancelado")
    assert lines[1] == (
        "rodada 22 · Qatar Grand Prix · ⚠ Em risco: conflitos na região "
        "(atualizado em 13/11)"
    )


@pytest.mark.usefixtures("frozen_agenda")
def test_status_when_everything_is_confirmed() -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "Todos os GPs de 2026 estão confirmados."


@pytest.fixture
def grid_env(
    race_env: FakeSessionSource,
    monkeypatch: pytest.MonkeyPatch,
    vegas_history: pd.DataFrame,
    madring_history: pd.DataFrame,
    season_2026: SeasonTables,
) -> FakeHistorySource:
    source = FakeHistorySource(
        {"vegas": vegas_history, "madring": madring_history}, season_2026
    )
    monkeypatch.setattr(
        cli,
        "build_history_store",
        lambda s: CuratedHistoryStore(FileCache(s.curated_dir), source),
    )
    return source


def test_grid_for_las_vegas(grid_env: FakeHistorySource, tmp_path: Path) -> None:
    result = runner.invoke(app, ["grid", "--season", "2026", "--round", "21"])

    assert result.exit_code == 0, result.output
    assert "Campeonato: Antonelli 390 x Verstappen 279 (diferença 111)" in result.stdout
    assert "Título decidido aqui? já decidido" in result.stdout
    assert "circuit_last_winner: Verstappen (2025)" in result.stdout
    draft = (
        tmp_path / "out" / "2026" / "21-las-vegas" / "circuit_preview" / "draft.json"
    )
    assert json.loads(draft.read_text(encoding="utf-8"))["segment"] == "circuit_preview"


def test_grid_defaults_to_next_gp(grid_env: FakeHistorySource) -> None:
    result = runner.invoke(app, ["grid"])

    assert result.exit_code == 0, result.output
    assert "Las Vegas Grand Prix · rodada 21" in result.stdout


def test_grid_for_circuit_without_history(grid_env: FakeHistorySource) -> None:
    result = runner.invoke(app, ["grid", "--round", "14"])

    assert result.exit_code == 0, result.output
    assert "circuit_first_race: Estreia em Madrid" in result.stdout
