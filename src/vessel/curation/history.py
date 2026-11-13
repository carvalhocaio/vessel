from datetime import datetime, timedelta

import pandas as pd

from vessel.cache import RESULTS_SETTLE, FileCache, Forever, Freshness, ParcFerme, Ttl
from vessel.curation.schema import HISTORY_DTYPES, STANDING_DTYPES, SeasonTables
from vessel.curation.store import fetch_frames, session_or_raise
from vessel.domain import Event, SessionKind
from vessel.schedule import last_finished_race
from vessel.sources.ports import HistorySource

PRESEASON_TTL = Ttl(timedelta(hours=1))


class CuratedHistoryStore:
    def __init__(self, cache: FileCache, source: HistorySource) -> None:
        self._cache = cache
        self._source = source

    def circuit(
        self, circuit_id: str, before_season: int, editions: int
    ) -> pd.DataFrame:
        key = f"history/circuits/{circuit_id}/before-{before_season}-last-{editions}"
        frames = fetch_frames(
            self._cache,
            {"results": f"{key}.parquet"},
            Forever(),
            {"results": HISTORY_DTYPES},
            lambda: {
                "results": self._source.circuit_results(
                    circuit_id, before_season, editions
                )
            },
        )
        return frames["results"]

    def season(self, events: tuple[Event, ...], now: datetime) -> SeasonTables:
        season = events[0].season
        frames = fetch_frames(
            self._cache,
            {
                "results": f"{season}/season/results.parquet",
                "standings": f"{season}/season/standings.parquet",
            },
            _season_freshness(events, now),
            {"results": HISTORY_DTYPES, "standings": STANDING_DTYPES},
            lambda: _season_frames(self._source.season(season)),
        )
        return SeasonTables(results=frames["results"], standings=frames["standings"])


def _season_freshness(events: tuple[Event, ...], now: datetime) -> Freshness:
    last = last_finished_race(events, now)
    if last is None:
        return PRESEASON_TTL
    return ParcFerme.after(session_or_raise(last, SessionKind.RACE), RESULTS_SETTLE)


def _season_frames(tables: SeasonTables) -> dict[str, pd.DataFrame]:
    conformed = tables.conformed()
    return {"results": conformed.results, "standings": conformed.standings}
