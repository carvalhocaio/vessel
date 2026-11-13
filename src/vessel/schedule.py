import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from vessel.domain import CalendarEntry, Event, EventRef, Session, SessionKind
from vessel.sources.ports import CalendarSource, ScheduleSource

logger = logging.getLogger(__name__)

MATCH_WINDOW = timedelta(days=3)


@dataclass(frozen=True, slots=True)
class Adjustment:
    event: EventRef
    kind: SessionKind
    before: datetime
    after: datetime


@dataclass(frozen=True, slots=True)
class Reconciliation:
    events: tuple[Event, ...]
    adjustments: tuple[Adjustment, ...]
    unconfirmed: tuple[tuple[EventRef, SessionKind], ...]


def reconcile(
    events: tuple[Event, ...], entries: tuple[CalendarEntry, ...]
) -> Reconciliation:
    adjustments: list[Adjustment] = []
    unconfirmed: list[tuple[EventRef, SessionKind]] = []
    reconciled: list[Event] = []
    for event in events:
        sessions: list[Session] = []
        for session in event.sessions:
            entry = _match(event.country, session, entries)
            if entry is None:
                unconfirmed.append((event.ref, session.kind))
                sessions.append(session)
                continue
            if entry.starts_at != session.starts_at:
                adjustments.append(
                    Adjustment(
                        event.ref, session.kind, session.starts_at, entry.starts_at
                    )
                )
            sessions.append(
                Session(
                    kind=session.kind, starts_at=entry.starts_at, ends_at=entry.ends_at
                )
            )
        sessions.sort(key=lambda session: session.starts_at)
        reconciled.append(
            Event.model_validate(event.model_dump() | {"sessions": tuple(sessions)})
        )
    return Reconciliation(tuple(reconciled), tuple(adjustments), tuple(unconfirmed))


def next_event(events: tuple[Event, ...], now: datetime) -> Event | None:
    upcoming = (event for event in events if event.ends_at and event.ends_at > now)
    return min(upcoming, key=lambda event: event.round, default=None)


def last_finished_race(events: tuple[Event, ...], now: datetime) -> Event | None:
    finished = (
        event
        for event in events
        if (race := event.session(SessionKind.RACE)) and race.ends_at <= now
    )
    return max(finished, key=lambda event: event.round, default=None)


class ReconciledSchedule:
    def __init__(self, base: ScheduleSource, calendar: CalendarSource | None) -> None:
        self._base = base
        self._calendar = calendar

    def events(self, season: int) -> tuple[Event, ...]:
        events = self._base.events(season)
        if self._calendar is None:
            return events
        result = reconcile(events, self._calendar.entries())
        for adjustment in result.adjustments:
            logger.warning(
                "%s %s moved from %s to %s by the official calendar",
                adjustment.event.name,
                adjustment.kind,
                adjustment.before.isoformat(),
                adjustment.after.isoformat(),
            )
        return result.events


def _match(
    country: str, session: Session, entries: tuple[CalendarEntry, ...]
) -> CalendarEntry | None:
    return next(
        (
            entry
            for entry in entries
            if entry.country == country
            and entry.kind is session.kind
            and abs(entry.starts_at - session.starts_at) <= MATCH_WINDOW
        ),
        None,
    )
