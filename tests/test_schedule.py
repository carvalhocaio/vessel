from datetime import UTC, date, datetime, timedelta

from tests.factories import FIXTURES, load_calendar_ics
from vessel.domain import CalendarEntry, Event, EventNotice, EventStatus, SessionKind
from vessel.event_status import EventStatusFile
from vessel.schedule import (
    ReconciledSchedule,
    last_finished,
    last_finished_race,
    next_event,
    reconcile,
)
from vessel.sources.calendar_source import parse_calendar

LAS_VEGAS = 21
QATAR = 22


def _by_round(events: tuple[Event, ...], round_: int) -> Event:
    return next(event for event in events if event.round == round_)


def test_official_calendar_confirms_matching_sessions(
    schedule_2026: tuple[Event, ...],
) -> None:
    result = reconcile(schedule_2026, parse_calendar(load_calendar_ics()))

    assert result.adjustments == ()
    unconfirmed_rounds = {ref.round for ref, _ in result.unconfirmed}
    assert LAS_VEGAS not in unconfirmed_rounds
    assert QATAR not in unconfirmed_rounds


def test_official_calendar_wins_when_times_differ(
    schedule_2026: tuple[Event, ...],
) -> None:
    qatar = _by_round(schedule_2026, QATAR)
    race = qatar.session(SessionKind.RACE)
    assert race is not None
    moved = CalendarEntry(
        country="Qatar",
        kind=SessionKind.RACE,
        starts_at=race.starts_at + timedelta(hours=1),
        ends_at=race.ends_at + timedelta(hours=1),
    )

    result = reconcile((qatar,), (moved,))

    (adjustment,) = result.adjustments
    assert adjustment.kind is SessionKind.RACE
    assert adjustment.after - adjustment.before == timedelta(hours=1)
    reconciled_race = result.events[0].session(SessionKind.RACE)
    assert reconciled_race is not None
    assert reconciled_race.starts_at == moved.starts_at


def test_entries_from_another_country_or_week_do_not_match(
    schedule_2026: tuple[Event, ...],
) -> None:
    qatar = _by_round(schedule_2026, QATAR)
    race = qatar.session(SessionKind.RACE)
    assert race is not None
    elsewhere = CalendarEntry(
        country="Bahrain",
        kind=SessionKind.RACE,
        starts_at=race.starts_at,
        ends_at=race.ends_at,
    )
    weeks_later = elsewhere.model_copy(
        update={"country": "Qatar", "starts_at": race.starts_at + timedelta(days=14)}
    )

    result = reconcile((qatar,), (elsewhere, weeks_later))

    assert result.events == (qatar,)
    assert len(result.unconfirmed) == len(qatar.sessions)


def test_next_event_is_the_first_not_finished(schedule_2026: tuple[Event, ...]) -> None:
    now = datetime(2026, 11, 13, 17, 0, tzinfo=UTC)

    event = next_event(schedule_2026, now)

    assert event is not None
    assert event.round == LAS_VEGAS


def test_next_event_keeps_current_weekend_until_race_ends(
    schedule_2026: tuple[Event, ...],
) -> None:
    qatar = _by_round(schedule_2026, QATAR)
    race = qatar.session(SessionKind.RACE)
    assert race is not None

    assert next_event(schedule_2026, race.starts_at) == qatar


def test_no_next_event_after_season(schedule_2026: tuple[Event, ...]) -> None:
    assert next_event(schedule_2026, datetime(2026, 12, 31, tzinfo=UTC)) is None


class FakeSchedule:
    def __init__(self, events: tuple[Event, ...]) -> None:
        self._events = events

    def events(self, season: int) -> tuple[Event, ...]:
        return self._events


class FakeCalendar:
    def entries(self) -> tuple[CalendarEntry, ...]:
        return parse_calendar(load_calendar_ics())


def test_reconciled_schedule_without_calendar_returns_base(
    schedule_2026: tuple[Event, ...],
) -> None:
    schedule = ReconciledSchedule(FakeSchedule(schedule_2026), calendar=None)

    assert schedule.events(2026) == schedule_2026


def test_reconciled_schedule_applies_calendar(
    schedule_2026: tuple[Event, ...],
) -> None:
    schedule = ReconciledSchedule(FakeSchedule(schedule_2026), FakeCalendar())

    vegas = _by_round(schedule.events(2026), LAS_VEGAS)

    race = vegas.session(SessionKind.RACE)
    assert race is not None
    assert race.ends_at == datetime(2026, 11, 22, 6, 0, tzinfo=UTC)


def test_last_finished_race_ignores_upcoming(schedule_2026: tuple[Event, ...]) -> None:
    event = last_finished_race(schedule_2026, datetime(2026, 11, 13, 17, tzinfo=UTC))

    assert event is not None
    assert event.round == 20


def test_last_finished_race_none_before_season(
    schedule_2026: tuple[Event, ...],
) -> None:
    assert last_finished_race(schedule_2026, datetime(2026, 1, 1, tzinfo=UTC)) is None


def test_last_finished_picks_current_gp_once_its_session_ended(
    schedule_2026: tuple[Event, ...],
) -> None:
    def long_run(event: Event) -> SessionKind:
        return event.long_run_session

    before = last_finished(
        schedule_2026, datetime(2026, 11, 6, 19, 30, tzinfo=UTC), long_run
    )
    after = last_finished(
        schedule_2026, datetime(2026, 11, 6, 21, tzinfo=UTC), long_run
    )

    assert before is not None
    assert before.round == 19
    assert after is not None
    assert after.round == 20


def test_last_finished_by_fixed_session(schedule_2026: tuple[Event, ...]) -> None:
    event = last_finished(
        schedule_2026,
        datetime(2026, 11, 13, 17, tzinfo=UTC),
        lambda _: SessionKind.SPRINT,
    )

    assert event is not None
    assert event.round == 17


class StaticSchedule:
    def __init__(self, events: tuple[Event, ...]) -> None:
        self._events = events

    def events(self, season: int) -> tuple[Event, ...]:
        return self._events


def test_reconciled_schedule_applies_status_after_calendar(
    schedule_2026: tuple[Event, ...],
) -> None:
    schedule = ReconciledSchedule(
        StaticSchedule(schedule_2026),
        None,
        EventStatusFile(FIXTURES / "event_status.toml"),
    )

    events = {event.round: event for event in schedule.events(2026)}

    assert events[22].status is EventStatus.AT_RISK


def test_next_event_skips_cancelled_gp(schedule_2026: tuple[Event, ...]) -> None:
    events = EventStatusFile(FIXTURES / "event_status.toml").apply(schedule_2026)

    event = next_event(events, datetime(2026, 11, 13, 17, tzinfo=UTC))

    assert event is not None
    assert event.round == QATAR


def test_last_finished_race_skips_cancelled_gp(
    schedule_2026: tuple[Event, ...],
) -> None:
    cancelled = EventNotice(
        status=EventStatus.CANCELLED, note="cancelado", updated_on=date(2026, 11, 1)
    )
    events = tuple(
        event.with_notice(cancelled) if event.round == 20 else event
        for event in schedule_2026
    )

    event = last_finished_race(events, datetime(2026, 11, 13, 17, tzinfo=UTC))

    assert event is not None
    assert event.round == 19
