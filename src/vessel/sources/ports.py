from typing import Protocol

import pandas as pd

from vessel.curation.schema import RaceTables, SeasonTables, SessionTables
from vessel.domain import (
    CalendarEntry,
    Event,
    RegulationDocument,
    SessionKind,
)


class SourceUnavailableError(RuntimeError):
    pass


class ScheduleSource(Protocol):
    def events(self, season: int) -> tuple[Event, ...]: ...


class CalendarSource(Protocol):
    def entries(self) -> tuple[CalendarEntry, ...]: ...


class SessionSource(Protocol):
    def race(self, event: Event) -> RaceTables: ...

    def session(self, event: Event, kind: SessionKind) -> SessionTables: ...


class HistorySource(Protocol):
    def circuit_results(
        self, circuit_id: str, before_season: int, editions: int
    ) -> pd.DataFrame: ...

    def season(self, season: int) -> SeasonTables: ...


class RegulationSource(Protocol):
    def documents(self) -> tuple[RegulationDocument, ...]: ...

    def pdf(self, document: RegulationDocument) -> bytes: ...

    def has_pdf(self, document: RegulationDocument) -> bool: ...
