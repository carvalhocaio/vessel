import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import fastf1
import pandas as pd
from fastf1 import plotting
from fastf1.ergast import Ergast
from fastf1.exceptions import DataNotLoadedError

from vessel.curation.schema import (
    DRIVER_DTYPES,
    LAP_DTYPES,
    RESULT_DTYPES,
    RaceTables,
    SessionTables,
    conform,
)
from vessel.domain import Event, SessionKind
from vessel.sources.ports import SourceUnavailableError

logger = logging.getLogger(__name__)

UNKNOWN_COMPOUND_COLOR = "#898781"
PIT_LANE_GRID = 0

FASTF1_SESSIONS = {
    SessionKind.PRACTICE_1: "FP1",
    SessionKind.PRACTICE_2: "FP2",
    SessionKind.PRACTICE_3: "FP3",
    SessionKind.SPRINT_QUALIFYING: "SQ",
    SessionKind.SPRINT: "Sprint",
    SessionKind.QUALIFYING: "Q",
    SessionKind.RACE: "R",
}


class FastF1SessionSource:
    def __init__(self, cache_dir: Path) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.configure(cache_dir=str(cache_dir))

    def race(self, event: Event) -> RaceTables:
        loaded = _load(event, SessionKind.RACE)
        return RaceTables(
            laps=loaded.laps,
            results=results_from_session(
                loaded.results, loaded.team_colors, loaded.nationalities
            ),
        )

    def session(self, event: Event, kind: SessionKind) -> SessionTables:
        loaded = _load(event, kind)
        return SessionTables(
            laps=loaded.laps,
            drivers=drivers_from_session(
                loaded.results, loaded.team_colors, loaded.nationalities
            ),
        )


@dataclass(frozen=True, slots=True)
class _Loaded:
    laps: pd.DataFrame
    results: pd.DataFrame
    team_colors: dict[str, str]
    nationalities: dict[str, str]


def _load(event: Event, kind: SessionKind) -> _Loaded:
    session = fastf1.get_session(event.season, event.round, FASTF1_SESSIONS[kind])
    session.load(laps=True, telemetry=False, weather=False, messages=False)
    try:
        laps = pd.DataFrame(session.laps)
    except DataNotLoadedError as exc:
        raise SourceUnavailableError(
            f"FastF1 has no lap timing for {event.name} {event.season} {kind.value}"
        ) from exc
    results = pd.DataFrame(session.results)
    return _Loaded(
        laps=laps_from_session(laps, plotting.get_compound_mapping(session)),
        results=results,
        team_colors={
            str(team): plotting.get_team_color(str(team), session)
            for team in results["TeamName"].dropna().unique()
        },
        nationalities=_nationalities(event),
    )


def _nationalities(event: Event) -> dict[str, str]:
    try:
        drivers = Ergast().get_driver_info(season=event.season, round=event.round)
    except Exception:
        logger.warning("driver nationalities unavailable for %s", event.name)
        return {}
    return dict(zip(drivers["driverCode"], drivers["driverNationality"], strict=True))


def laps_from_session(
    laps: pd.DataFrame, compound_colors: Mapping[str, str]
) -> pd.DataFrame:
    compounds = laps["Compound"].astype("string")
    curated = pd.DataFrame(
        {
            "driver": laps["Driver"],
            "team": laps["Team"],
            "lap": laps["LapNumber"],
            "lap_time_s": pd.to_timedelta(laps["LapTime"]).dt.total_seconds(),
            "stint": laps["Stint"],
            "compound": compounds,
            "compound_color": compounds.map(
                lambda name: compound_colors.get(str(name), UNKNOWN_COMPOUND_COLOR)
            ),
            "tyre_life": laps["TyreLife"],
            "position": laps["Position"],
            "pit_in": laps["PitInTime"].notna(),
            "pit_out": laps["PitOutTime"].notna(),
            "track_status": laps["TrackStatus"].fillna(""),
            "is_accurate": laps["IsAccurate"].fillna(value=False),
        }
    )
    return conform(curated, LAP_DTYPES)


def results_from_session(
    results: pd.DataFrame,
    team_colors: Mapping[str, str],
    nationalities: Mapping[str, str],
) -> pd.DataFrame:
    grid = pd.to_numeric(results["GridPosition"], errors="coerce")
    curated = _driver_columns(results, team_colors, nationalities).assign(
        **{
            "grid": grid.where(grid != PIT_LANE_GRID),
            "finish": pd.to_numeric(results["Position"], errors="coerce"),
            "classified": results["ClassifiedPosition"].astype(str).str.isdigit(),
            "status": results["Status"],
            "points": pd.to_numeric(results["Points"], errors="coerce"),
        }
    )
    return conform(curated.sort_values("finish"), RESULT_DTYPES)


def drivers_from_session(
    results: pd.DataFrame,
    team_colors: Mapping[str, str],
    nationalities: Mapping[str, str],
) -> pd.DataFrame:
    curated = _driver_columns(results, team_colors, nationalities)
    return conform(curated.sort_values("driver"), DRIVER_DTYPES)


def _driver_columns(
    results: pd.DataFrame,
    team_colors: Mapping[str, str],
    nationalities: Mapping[str, str],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "driver": results["Abbreviation"],
            "name": results["LastName"],
            "team": results["TeamName"],
            "team_color": results["TeamName"].map(team_colors),
            "nationality": results["Abbreviation"].map(nationalities),
        }
    )
