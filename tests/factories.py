from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

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
