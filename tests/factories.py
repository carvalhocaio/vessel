from datetime import UTC, datetime, timedelta

from vessel.domain import Event, EventFormat, Session, SessionKind

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
        round=21,
        name="São Paulo Grand Prix",
        location="São Paulo",
        country="Brazil",
        format=EventFormat.CONVENTIONAL,
        sessions=tuple(make_session(kind, start) for kind, start in SAO_PAULO_2026),
    )
