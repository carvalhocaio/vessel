import io
import logging

import pandas as pd

from vessel.cache import RESULTS_SETTLE, FileCache, ParcFerme
from vessel.curation.schema import LAP_DTYPES, RESULT_DTYPES, RaceTables, conform
from vessel.domain import Event, Session, SessionKind
from vessel.sources.ports import SessionSource

logger = logging.getLogger(__name__)

LAPS_FILE = "laps.parquet"
RESULTS_FILE = "results.parquet"


class MissingRaceError(ValueError):
    pass


def race_session(event: Event) -> Session:
    session = event.session(SessionKind.RACE)
    if session is None:
        raise MissingRaceError(f"{event.name} has no race session")
    return session


def race_prefix(event: Event) -> str:
    return f"{event.season}/{event.slug}/race"


class CuratedRaceStore:
    def __init__(self, cache: FileCache, source: SessionSource) -> None:
        self._cache = cache
        self._source = source

    def tables(self, event: Event) -> RaceTables:
        laps_key, results_key = _keys(event)
        freshness = ParcFerme.after(race_session(event), RESULTS_SETTLE)
        laps = self._cache.get(laps_key, freshness)
        results = self._cache.get(results_key, freshness)
        if laps is not None and results is not None:
            return _decode(laps, results)
        try:
            tables = self._source.race(event).conformed()
        except Exception:
            stale = self._stale(laps_key, results_key)
            if stale is None:
                raise
            logger.warning("serving stale curated race for %s", event.name)
            return stale
        self._cache.put(laps_key, _encode(tables.laps))
        self._cache.put(results_key, _encode(tables.results))
        return tables

    def _stale(self, laps_key: str, results_key: str) -> RaceTables | None:
        laps = self._cache.read(laps_key)
        results = self._cache.read(results_key)
        if laps is None or results is None:
            return None
        return _decode(laps.data, results.data)


def _keys(event: Event) -> tuple[str, str]:
    prefix = race_prefix(event)
    return f"{prefix}/{LAPS_FILE}", f"{prefix}/{RESULTS_FILE}"


def _encode(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _decode(laps: bytes, results: bytes) -> RaceTables:
    return RaceTables(
        laps=conform(pd.read_parquet(io.BytesIO(laps)), LAP_DTYPES),
        results=conform(pd.read_parquet(io.BytesIO(results)), RESULT_DTYPES),
    )
