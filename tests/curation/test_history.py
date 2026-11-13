from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from tests.factories import FakeHistorySource
from vessel.cache import FileCache
from vessel.curation import SeasonTables
from vessel.curation.history import CuratedHistoryStore
from vessel.domain import Event

AFTER_SAO_PAULO_LOCK = datetime(2026, 11, 13, 17, tzinfo=UTC)
BEFORE_SAO_PAULO_LOCK = datetime(2026, 11, 8, 20, tzinfo=UTC)


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_store(
    root: Path,
    history: pd.DataFrame,
    season: SeasonTables,
    now: datetime,
) -> tuple[CuratedHistoryStore, FakeHistorySource, Clock]:
    clock = Clock(now)
    source = FakeHistorySource({"vegas": history}, season)
    return CuratedHistoryStore(FileCache(root, clock), source), source, clock


def test_circuit_history_is_cached_forever(
    tmp_path: Path, vegas_history: pd.DataFrame, season_2026: SeasonTables
) -> None:
    store, source, clock = make_store(
        tmp_path, vegas_history, season_2026, AFTER_SAO_PAULO_LOCK
    )
    store.circuit("vegas", 2026, 10)
    clock.now = datetime(2030, 1, 1, tzinfo=UTC)

    history = store.circuit("vegas", 2026, 10)

    assert source.calls == 1
    assert (tmp_path / "history/circuits/vegas/before-2026-last-10.parquet").is_file()
    pd.testing.assert_frame_equal(history, vegas_history)


def test_season_settles_after_last_finished_race(
    tmp_path: Path,
    vegas_history: pd.DataFrame,
    season_2026: SeasonTables,
    schedule_2026: tuple[Event, ...],
) -> None:
    store, source, clock = make_store(
        tmp_path, vegas_history, season_2026, BEFORE_SAO_PAULO_LOCK
    )
    store.season(schedule_2026, BEFORE_SAO_PAULO_LOCK)
    clock.now = AFTER_SAO_PAULO_LOCK
    store.season(schedule_2026, AFTER_SAO_PAULO_LOCK)
    store.season(schedule_2026, AFTER_SAO_PAULO_LOCK)

    assert source.calls == 2
    assert (tmp_path / "2026/season/standings.parquet").is_file()


def test_season_serves_last_tables_when_jolpica_fails(
    tmp_path: Path,
    vegas_history: pd.DataFrame,
    season_2026: SeasonTables,
    schedule_2026: tuple[Event, ...],
) -> None:
    store, source, clock = make_store(
        tmp_path, vegas_history, season_2026, BEFORE_SAO_PAULO_LOCK
    )
    store.season(schedule_2026, BEFORE_SAO_PAULO_LOCK)
    clock.now = AFTER_SAO_PAULO_LOCK
    source.error = RuntimeError("Jolpica down")

    tables = store.season(schedule_2026, AFTER_SAO_PAULO_LOCK)

    pd.testing.assert_frame_equal(tables.standings, season_2026.standings)


def test_failure_without_saved_tables_propagates(
    tmp_path: Path, vegas_history: pd.DataFrame, season_2026: SeasonTables
) -> None:
    store, source, _ = make_store(
        tmp_path, vegas_history, season_2026, AFTER_SAO_PAULO_LOCK
    )
    source.error = RuntimeError("Jolpica down")

    with pytest.raises(RuntimeError, match="Jolpica down"):
        store.circuit("vegas", 2026, 10)
