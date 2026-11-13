import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
import icalendar

from vessel.cache import FileCache, Ttl
from vessel.domain import CalendarEntry, SessionKind

CACHE_KEY = "calendar/f1.ics"
DEFAULT_MAX_AGE = timedelta(hours=6)

_SUMMARY = re.compile(r"FORMULA 1 .+ \d{4} - (?P<session>.+?)(?:\s*\(TBC\))?\s*$")

CALENDAR_SESSIONS = {
    "Practice 1": SessionKind.PRACTICE_1,
    "Practice 2": SessionKind.PRACTICE_2,
    "Practice 3": SessionKind.PRACTICE_3,
    "Sprint Qualifying": SessionKind.SPRINT_QUALIFYING,
    "Sprint Qualification": SessionKind.SPRINT_QUALIFYING,
    "Sprint": SessionKind.SPRINT,
    "Qualifying": SessionKind.QUALIFYING,
    "Race": SessionKind.RACE,
}

HttpGet = Callable[[str], bytes]


def http_get(url: str) -> bytes:
    response = httpx.get(url, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    return response.content


class ICalCalendarSource:
    def __init__(
        self,
        url: str,
        cache: FileCache,
        get: HttpGet = http_get,
        max_age: timedelta = DEFAULT_MAX_AGE,
    ) -> None:
        self._url = url
        self._cache = cache
        self._get = get
        self._max_age = max_age

    def entries(self) -> tuple[CalendarEntry, ...]:
        ics = self._cache.fetch(
            CACHE_KEY, Ttl(self._max_age), lambda: self._get(self._url),
        )
        return parse_calendar(ics)


def parse_calendar(ics: bytes) -> tuple[CalendarEntry, ...]:
    calendar = icalendar.Calendar.from_ical(ics)
    entries = (_entry(component) for component in calendar.walk("VEVENT"))
    return tuple(
        sorted(
            (entry for entry in entries if entry is not None),
            key=lambda entry: entry.starts_at,
        )
    )


def _entry(component: icalendar.Component) -> CalendarEntry | None:
    match = _SUMMARY.search(str(component.get("SUMMARY", "")))
    kind = CALENDAR_SESSIONS.get(match["session"]) if match else None
    if kind is None or "DTEND" not in component:
        return None
    starts_at = component.decoded("DTSTART")
    ends_at = component.decoded("DTEND")
    if not isinstance(starts_at, datetime) or not isinstance(ends_at, datetime):
        return None
    return CalendarEntry(
        country=str(component.get("LOCATION", "")),
        kind=kind,
        starts_at=_as_utc(starts_at),
        ends_at=_as_utc(ends_at),
    )


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)
