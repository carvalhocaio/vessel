from collections.abc import Hashable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import fastf1
import pandas as pd

from vessel.domain import Event, EventFormat, Session, SessionKind

SESSION_KINDS = {
    "Practice 1": SessionKind.PRACTICE_1,
    "Practice 2": SessionKind.PRACTICE_2,
    "Practice 3": SessionKind.PRACTICE_3,
    "Sprint Shootout": SessionKind.SPRINT_QUALIFYING,
    "Sprint Qualifying": SessionKind.SPRINT_QUALIFYING,
    "Sprint": SessionKind.SPRINT,
    "Qualifying": SessionKind.QUALIFYING,
    "Race": SessionKind.RACE,
}

EVENT_FORMATS = {
    "conventional": EventFormat.CONVENTIONAL,
    "sprint": EventFormat.SPRINT,
    "sprint_shootout": EventFormat.SPRINT,
    "sprint_qualifying": EventFormat.SPRINT,
}

SESSION_DURATIONS = {SessionKind.RACE: timedelta(hours=2)}
DEFAULT_DURATION = timedelta(hours=1)
SESSION_SLOTS = range(1, 6)

Row = Mapping[Hashable, Any]


class FastF1ScheduleSource:
    def __init__(self, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.configure(cache_dir=str(cache_dir))

    def events(self, season: int) -> tuple[Event, ...]:
        schedule = fastf1.get_event_schedule(season, include_testing=False)
        return events_from_schedule(schedule)


def events_from_schedule(schedule: pd.DataFrame) -> tuple[Event, ...]:
    rows = schedule.to_dict("records")
    return tuple(_event(row) for row in rows if row["EventFormat"] in EVENT_FORMATS)


def _event(row: Row) -> Event:
    sessions = sorted(
        (session for slot in SESSION_SLOTS if (session := _session(row, slot))),
        key=lambda session: session.starts_at,
    )
    return Event(
        season=pd.Timestamp(row["EventDate"]).year,
        round=int(row["RoundNumber"]),
        name=str(row["EventName"]),
        location=str(row["Location"]),
        country=str(row["Country"]),
        format=EVENT_FORMATS[str(row["EventFormat"])],
        sessions=tuple(sessions),
    )


def _session(row: Row, slot: int) -> Session | None:
    kind = SESSION_KINDS.get(str(row[f"Session{slot}"]))
    starts_at = _utc(row[f"Session{slot}DateUtc"])
    if kind is None or starts_at is None:
        return None
    duration = SESSION_DURATIONS.get(kind, DEFAULT_DURATION)
    return Session(kind=kind, starts_at=starts_at, ends_at=starts_at + duration)


def _utc(value: Any) -> datetime | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).to_pydatetime().replace(tzinfo=UTC)
