from pathlib import Path
from typing import Protocol

import pandas as pd

from vessel.analytics.registry import CalcInputs, RegulationKey
from vessel.cache import FileCache
from vessel.curation.history import circuit_history_key, season_keys
from vessel.curation.regulations import articles_key
from vessel.curation.schema import (
    ARTICLE_DTYPES,
    DRIVER_DTYPES,
    HISTORY_DTYPES,
    LAP_DTYPES,
    RESULT_DTYPES,
    STANDING_DTYPES,
    RaceTables,
    SeasonTables,
    SessionTables,
)
from vessel.curation.store import Schemas, decode_frames, session_key
from vessel.domain import (
    CircuitHistoryRef,
    RegulationTableRef,
    SeasonTableRef,
    SessionKind,
    SessionTableRef,
    TableRef,
)


class MissingCuratedTableError(FileNotFoundError):
    pass


class TableLoader(Protocol):
    def load(self, refs: tuple[TableRef, ...]) -> CalcInputs: ...


class CuratedTables:
    def __init__(self, curated_dir: Path) -> None:
        self._cache = FileCache(curated_dir)

    def load(self, refs: tuple[TableRef, ...]) -> CalcInputs:
        race: RaceTables | None = None
        session: SessionTables | None = None
        history: pd.DataFrame | None = None
        season: SeasonTables | None = None
        regulations: dict[RegulationKey, pd.DataFrame] = {}
        for ref in refs:
            match ref:
                case SessionTableRef(session_kind=SessionKind.RACE):
                    frames = self._read(ref, _session_keys(ref, "results"), _RACE)
                    race = RaceTables(laps=frames["laps"], results=frames["results"])
                case SessionTableRef():
                    frames = self._read(ref, _session_keys(ref, "drivers"), _SESSION)
                    session = SessionTables(
                        laps=frames["laps"], drivers=frames["drivers"]
                    )
                case CircuitHistoryRef():
                    key = circuit_history_key(
                        ref.circuit_id, ref.before_season, ref.editions
                    )
                    history = self._read(ref, {"results": key}, _HISTORY)["results"]
                case SeasonTableRef():
                    frames = self._read(ref, season_keys(ref.season), _SEASON)
                    season = SeasonTables(
                        results=frames["results"], standings=frames["standings"]
                    )
                case RegulationTableRef():
                    key = articles_key(ref.season, ref.section, ref.issue)
                    articles = self._read(ref, {"articles": key}, _REGULATION)
                    regulations[(ref.season, ref.section.value, ref.issue)] = articles[
                        "articles"
                    ]
        return CalcInputs(
            race_tables=race,
            session_tables=session,
            history_table=history,
            season_tables=season,
            regulation_tables=regulations,
        )

    def _read(
        self, ref: TableRef, keys: dict[str, str], schemas: Schemas
    ) -> dict[str, pd.DataFrame]:
        raw = {}
        for name, key in keys.items():
            entry = self._cache.read(key)
            if entry is None:
                raise MissingCuratedTableError(
                    f"curated table {key} is missing; generate it with: "
                    f"{producing_command(ref)}"
                )
            raw[name] = entry.data
        return decode_frames(raw, schemas)


def producing_command(ref: TableRef) -> str:
    match ref:
        case SessionTableRef(session_kind=SessionKind.RACE):
            return f"uv run vessel race --season {ref.season} --round {ref.round}"
        case SessionTableRef():
            return (
                f"uv run vessel long-run --season {ref.season} --round {ref.round} "
                f"--session {ref.session_kind.value}"
            )
        case CircuitHistoryRef():
            return f"uv run vessel grid --season {ref.before_season}"
        case SeasonTableRef():
            return f"uv run vessel grid --season {ref.season}"
        case RegulationTableRef():
            return "uv run vessel regs sync --all"


def _session_keys(ref: SessionTableRef, second: str) -> dict[str, str]:
    return {
        name: session_key(ref.season, ref.slug, ref.session_kind, name)
        for name in ("laps", second)
    }


_RACE: Schemas = {"laps": LAP_DTYPES, "results": RESULT_DTYPES}
_SESSION: Schemas = {"laps": LAP_DTYPES, "drivers": DRIVER_DTYPES}
_HISTORY: Schemas = {"results": HISTORY_DTYPES}
_SEASON: Schemas = {"results": HISTORY_DTYPES, "standings": STANDING_DTYPES}
_REGULATION: Schemas = {"articles": ARTICLE_DTYPES}
