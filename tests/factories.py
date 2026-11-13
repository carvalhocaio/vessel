from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from vessel.curation import RaceTables, SessionTables
from vessel.domain import Event, EventFormat, Session, SessionKind
from vessel.sources.fastf1_schedule import events_from_schedule

FIXTURES = Path(__file__).parent / "fixtures"

SAO_PAULO_2026 = (
    (SessionKind.PRACTICE_1, datetime(2026, 11, 6, 15, 30, tzinfo=UTC)),
    (SessionKind.PRACTICE_2, datetime(2026, 11, 6, 19, 0, tzinfo=UTC)),
    (SessionKind.PRACTICE_3, datetime(2026, 11, 7, 14, 30, tzinfo=UTC)),
    (SessionKind.QUALIFYING, datetime(2026, 11, 7, 18, 0, tzinfo=UTC)),
    (SessionKind.RACE, datetime(2026, 11, 8, 17, 0, tzinfo=UTC)),
)


def make_session(kind: SessionKind, starts_at: datetime) -> Session:
    duration = timedelta(hours=2 if kind is SessionKind.RACE else 1)
    return Session(kind=kind, starts_at=starts_at, ends_at=starts_at + duration)


def make_sao_paulo() -> Event:
    return Event(
        season=2026,
        round=20,
        name="São Paulo Grand Prix",
        location="São Paulo",
        country="Brazil",
        format=EventFormat.CONVENTIONAL,
        sessions=tuple(make_session(kind, start) for kind, start in SAO_PAULO_2026),
    )


def load_schedule_2026() -> tuple[Event, ...]:
    return events_from_schedule(pd.read_csv(FIXTURES / "fastf1_schedule_2026.csv"))


def load_calendar_ics() -> bytes:
    return (FIXTURES / "f1_calendar.ics").read_bytes()


def load_race_2026_20() -> RaceTables:
    return RaceTables(
        laps=pd.read_parquet(FIXTURES / "race_2026_20_laps.parquet"),
        results=pd.read_parquet(FIXTURES / "race_2026_20_results.parquet"),
    ).conformed()


def load_session_tables(name: str) -> SessionTables:
    return SessionTables(
        laps=pd.read_parquet(FIXTURES / f"{name}_laps.parquet"),
        drivers=pd.read_parquet(FIXTURES / f"{name}_drivers.parquet"),
    ).conformed()


def make_singapore() -> Event:
    return next(event for event in load_schedule_2026() if event.round == 17)


def load_fastf1_race_sample() -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_parquet(FIXTURES / "fastf1_race_2026_20_laps_sample.parquet"),
        pd.read_parquet(FIXTURES / "fastf1_race_2026_20_results_sample.parquet"),
    )


class FakeSessionSource:
    def __init__(
        self,
        tables: RaceTables,
        sessions: dict[SessionKind, SessionTables] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._tables = tables
        self.sessions = sessions or {}
        self.error = error
        self.calls = 0

    def race(self, event: Event) -> RaceTables:
        self._call()
        return self._tables

    def session(self, event: Event, kind: SessionKind) -> SessionTables:
        self._call()
        return self.sessions[kind]

    def _call(self) -> None:
        self.calls += 1
        if self.error is not None:
            raise self.error
