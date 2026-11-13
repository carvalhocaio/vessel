import io
import logging
from collections.abc import Callable, Mapping
from datetime import timedelta

import pandas as pd

from vessel.cache import RESULTS_SETTLE, TIMING_SETTLE, FileCache, ParcFerme
from vessel.curation.schema import (
    DRIVER_DTYPES,
    LAP_DTYPES,
    RESULT_DTYPES,
    RaceTables,
    SessionTables,
    conform,
)
from vessel.domain import Event, Session, SessionKind
from vessel.sources.ports import SessionSource

logger = logging.getLogger(__name__)

PARQUET_SUFFIX = ".parquet"

Frames = dict[str, pd.DataFrame]
Schemas = Mapping[str, dict[str, str]]


class MissingSessionError(ValueError):
    pass


def session_or_raise(event: Event, kind: SessionKind) -> Session:
    session = event.session(kind)
    if session is None:
        raise MissingSessionError(f"{event.name} has no {kind.value} session")
    return session


def session_prefix(event: Event, kind: SessionKind) -> str:
    return f"{event.season}/{event.slug}/{kind.value}"


class CuratedSessionStore:
    def __init__(self, cache: FileCache, source: SessionSource) -> None:
        self._cache = cache
        self._source = source

    def race(self, event: Event) -> RaceTables:
        frames = self._cached(
            event,
            SessionKind.RACE,
            RESULTS_SETTLE,
            {"laps": LAP_DTYPES, "results": RESULT_DTYPES},
            lambda: _frames(self._source.race(event).conformed()),
        )
        return RaceTables(laps=frames["laps"], results=frames["results"])

    def session(self, event: Event, kind: SessionKind) -> SessionTables:
        frames = self._cached(
            event,
            kind,
            TIMING_SETTLE,
            {"laps": LAP_DTYPES, "drivers": DRIVER_DTYPES},
            lambda: _frames(self._source.session(event, kind).conformed()),
        )
        return SessionTables(laps=frames["laps"], drivers=frames["drivers"])

    def _cached(
        self,
        event: Event,
        kind: SessionKind,
        settle: timedelta,
        schemas: Schemas,
        load: Callable[[], Frames],
    ) -> Frames:
        keys = {name: _key(event, kind, name) for name in schemas}
        freshness = ParcFerme.after(session_or_raise(event, kind), settle)
        fresh = {
            name: data
            for name, key in keys.items()
            if (data := self._cache.get(key, freshness)) is not None
        }
        if len(fresh) == len(keys):
            return _decode(fresh, schemas)
        try:
            frames = load()
        except Exception:
            stale = {
                name: entry.data
                for name, key in keys.items()
                if (entry := self._cache.read(key)) is not None
            }
            if len(stale) < len(keys):
                raise
            logger.warning("serving stale curated %s for %s", kind.value, event.name)
            return _decode(stale, schemas)
        for name, key in keys.items():
            self._cache.put(key, _encode(frames[name]))
        return frames


def _frames(tables: RaceTables | SessionTables) -> Frames:
    if isinstance(tables, RaceTables):
        return {"laps": tables.laps, "results": tables.results}
    return {"laps": tables.laps, "drivers": tables.drivers}


def _key(event: Event, kind: SessionKind, name: str) -> str:
    return f"{session_prefix(event, kind)}/{name}{PARQUET_SUFFIX}"


def _encode(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _decode(data: Mapping[str, bytes], schemas: Schemas) -> Frames:
    return {
        name: conform(pd.read_parquet(io.BytesIO(raw)), schemas[name])
        for name, raw in data.items()
    }
