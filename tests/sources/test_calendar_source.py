from datetime import UTC, datetime
from pathlib import Path

from tests.factories import load_calendar_ics
from vessel.cache import FileCache
from vessel.domain import SessionKind
from vessel.sources.calendar_source import ICalCalendarSource, parse_calendar

TBC_ICS = b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
BEGIN:VEVENT\r
UID:tbc\r
SUMMARY:\xf0\x9f\x8f\x81 FORMULA 1 SOME GRAND PRIX 2027 - Race (TBC)\r
LOCATION:Somewhere\r
DTSTART;VALUE=DATE:20270314\r
DTEND;VALUE=DATE:20270315\r
END:VEVENT\r
END:VCALENDAR\r
"""


def test_parses_sessions_and_skips_welcome_event() -> None:
    entries = parse_calendar(load_calendar_ics())

    assert len(entries) == 10
    first = entries[0]
    assert first.country == "United States"
    assert first.kind is SessionKind.PRACTICE_1
    assert first.starts_at == datetime(2026, 11, 20, 0, 30, tzinfo=UTC)
    assert first.ends_at == datetime(2026, 11, 20, 1, 30, tzinfo=UTC)


def test_entries_are_chronological() -> None:
    entries = parse_calendar(load_calendar_ics())

    assert [e.starts_at for e in entries] == sorted(e.starts_at for e in entries)


def test_skips_all_day_sessions_still_to_be_confirmed() -> None:
    assert parse_calendar(TBC_ICS) == ()


class CountingGet:
    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        return load_calendar_ics()


def test_source_downloads_once_and_reuses_cache(tmp_path: Path) -> None:
    get = CountingGet()
    source = ICalCalendarSource(
        "https://calendar.test/f1.ics", FileCache(tmp_path), get
    )

    first = source.entries()
    second = source.entries()

    assert first == second
    assert get.urls == ["https://calendar.test/f1.ics"]
