from typing import Protocol

from vessel.domain import CalendarEntry, Event


class ScheduleSource(Protocol):
    def events(self, season: int) -> tuple[Event, ...]: ...


class CalendarSource(Protocol):
    def entries(self) -> tuple[CalendarEntry, ...]: ...
