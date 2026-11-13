from datetime import UTC, datetime, timedelta

import pandas as pd

from tests.factories import FIXTURES
from vessel.domain import Event, EventFormat, SessionKind
from vessel.sources.fastf1_schedule import events_from_schedule


def _by_round(events: tuple[Event, ...], round_: int) -> Event:
    return next(event for event in events if event.round == round_)


def test_maps_every_round(schedule_2026: tuple[Event, ...]) -> None:
    assert [event.round for event in schedule_2026] == list(range(1, 24))
    assert {event.season for event in schedule_2026} == {2026}


def test_maps_identity_fields(schedule_2026: tuple[Event, ...]) -> None:
    qatar = _by_round(schedule_2026, 22)

    assert qatar.name == "Qatar Grand Prix"
    assert qatar.location == "Lusail"
    assert qatar.country == "Qatar"
    assert qatar.format is EventFormat.CONVENTIONAL


def test_sessions_are_utc_with_default_durations(
    schedule_2026: tuple[Event, ...],
) -> None:
    qatar = _by_round(schedule_2026, 22)
    practice = qatar.session(SessionKind.PRACTICE_1)
    race = qatar.session(SessionKind.RACE)

    assert practice is not None
    assert race is not None
    assert practice.starts_at == datetime(2026, 11, 27, 13, 30, tzinfo=UTC)
    assert practice.ends_at - practice.starts_at == timedelta(hours=1)
    assert race.ends_at - race.starts_at == timedelta(hours=2)


def test_sprint_weekend_maps_sprint_sessions(schedule_2026: tuple[Event, ...]) -> None:
    china = _by_round(schedule_2026, 2)

    assert china.format is EventFormat.SPRINT
    assert [session.kind for session in china.sessions] == [
        SessionKind.PRACTICE_1,
        SessionKind.SPRINT_QUALIFYING,
        SessionKind.SPRINT,
        SessionKind.QUALIFYING,
        SessionKind.RACE,
    ]
    assert china.long_run_session is SessionKind.SPRINT


def test_skips_testing_and_sessions_without_date() -> None:
    schedule = pd.read_csv(FIXTURES / "fastf1_schedule_2026.csv").head(1)
    testing = schedule.assign(EventFormat="testing")
    undated = schedule.assign(Session5DateUtc=None)

    assert events_from_schedule(testing) == ()
    (event,) = events_from_schedule(undated)
    assert event.session(SessionKind.RACE) is None
