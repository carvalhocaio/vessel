from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from tests.factories import FakeSessionSource
from vessel.cache import FileCache
from vessel.curation import RaceTables
from vessel.curation.race import CuratedRaceStore, MissingRaceError
from vessel.domain import Event

BEFORE_LOCK = datetime(2026, 11, 8, 20, tzinfo=UTC)
AFTER_LOCK = datetime(2026, 11, 10, 12, tzinfo=UTC)


class Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def make_store(
    root: Path, tables: RaceTables, now: datetime
) -> tuple[CuratedRaceStore, FakeSessionSource, Clock]:
    clock = Clock(now)
    source = FakeSessionSource(tables)
    return CuratedRaceStore(FileCache(root, clock), source), source, clock


def test_curates_parquet_under_season_and_slug(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    store, source, _ = make_store(tmp_path, race_2026_20, AFTER_LOCK)

    tables = store.tables(sao_paulo)

    assert source.calls == 1
    race_dir = tmp_path / "2026" / "20-sao-paulo" / "race"
    assert (race_dir / "laps.parquet").is_file()
    assert (race_dir / "results.parquet").is_file()
    pd.testing.assert_frame_equal(tables.laps, race_2026_20.laps)


def test_parc_ferme_tables_are_not_reloaded(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    store, source, clock = make_store(tmp_path, race_2026_20, AFTER_LOCK)
    store.tables(sao_paulo)
    clock.now = datetime(2027, 1, 1, tzinfo=UTC)

    tables = store.tables(sao_paulo)

    assert source.calls == 1
    pd.testing.assert_frame_equal(tables.results, race_2026_20.results)


def test_tables_written_before_lock_are_reloaded(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    store, source, clock = make_store(tmp_path, race_2026_20, BEFORE_LOCK)
    store.tables(sao_paulo)
    clock.now = AFTER_LOCK

    store.tables(sao_paulo)

    assert source.calls == 2


def test_serves_last_tables_when_source_fails(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    store, source, clock = make_store(tmp_path, race_2026_20, BEFORE_LOCK)
    store.tables(sao_paulo)
    clock.now = AFTER_LOCK
    source.error = RuntimeError("timing offline")

    tables = store.tables(sao_paulo)

    pd.testing.assert_frame_equal(tables.laps, race_2026_20.laps)


def test_propagates_failure_without_saved_tables(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    store, source, _ = make_store(tmp_path, race_2026_20, AFTER_LOCK)
    source.error = RuntimeError("timing offline")

    with pytest.raises(RuntimeError, match="offline"):
        store.tables(sao_paulo)


def test_requires_a_race_session(
    tmp_path: Path, sao_paulo: Event, race_2026_20: RaceTables
) -> None:
    store, _, _ = make_store(tmp_path, race_2026_20, AFTER_LOCK)
    no_race = sao_paulo.model_copy(update={"sessions": sao_paulo.sessions[:-1]})

    with pytest.raises(MissingRaceError):
        store.tables(no_race)
