from typing import Protocol

from vessel.curation.schema import RaceTables
from vessel.domain import CalendarEntry, Event


class SourceUnavailableError(RuntimeError):
    pass


class ScheduleSource(Protocol):
    def events(self, season: int) -> tuple[Event, ...]: ...


class CalendarSource(Protocol):
    def entries(self) -> tuple[CalendarEntry, ...]: ...


class SessionSource(Protocol):
    def race(self, event: Event) -> RaceTables: ...
