from collections.abc import Iterator
from typing import Any

import pandas as pd
from fastf1.ergast import Ergast

from vessel.curation.schema import (
    HISTORY_DTYPES,
    STANDING_DTYPES,
    SeasonTables,
    conform,
)

PAGE_LIMIT = 100
RACE = "race"
SPRINT = "sprint"


class JolpicaSource:
    def __init__(self, ergast: Ergast | None = None) -> None:
        self._ergast = ergast or Ergast()

    def circuit_results(
        self, circuit_id: str, before_season: int, editions: int
    ) -> pd.DataFrame:
        races = pd.concat(
            list(
                _frames(
                    self._ergast.get_race_schedule(
                        None, circuit=circuit_id, limit=PAGE_LIMIT
                    )
                )
            ),
            ignore_index=True,
        )
        past = races[races["season"] < before_season].sort_values(
            ["season", "round"], ascending=False
        )
        collected: list[pd.DataFrame] = []
        for race in past.to_dict("records"):
            if len(collected) == editions:
                break
            response = self._ergast.get_race_results(
                season=int(race["season"]), round=int(race["round"])
            )
            frame = results_from_ergast(response.description, response.content, RACE)
            if not frame.empty:
                collected.append(frame)
        return _concat(collected)

    def season(self, season: int) -> SeasonTables:
        races = self._ergast.get_race_results(season=season, limit=PAGE_LIMIT)
        sprints = self._ergast.get_sprint_results(season=season, limit=PAGE_LIMIT)
        standings = self._ergast.get_driver_standings(season=season)
        results = _concat(
            [
                results_from_ergast(page.description, page.content, kind)
                for response, kind in ((races, RACE), (sprints, SPRINT))
                for page in _pages(response)
            ]
        )
        table = standings.content[0] if standings.content else pd.DataFrame()
        return SeasonTables(
            results=results, standings=standings_from_ergast(table)
        ).conformed()


def results_from_ergast(
    description: pd.DataFrame, content: list[pd.DataFrame], session: str
) -> pd.DataFrame:
    frames = []
    for race, results in zip(description.to_dict("records"), content, strict=True):
        if results.empty:
            continue
        frames.append(
            pd.DataFrame(
                {
                    "season": race["season"],
                    "round": race["round"],
                    "circuit_id": race["circuitId"],
                    "race_name": race["raceName"],
                    "date": pd.Timestamp(race["raceDate"]).strftime("%Y-%m-%d"),
                    "session": session,
                    "driver": results["driverCode"],
                    "name": results["familyName"],
                    "nationality": results["driverNationality"],
                    "team": results["constructorName"],
                    "grid": pd.to_numeric(results["grid"], errors="coerce"),
                    "finish": pd.to_numeric(results["position"], errors="coerce"),
                    "position_text": results["positionText"].astype(str),
                    "status": results["status"],
                    "points": pd.to_numeric(results["points"], errors="coerce"),
                }
            )
        )
    return _concat(frames)


def standings_from_ergast(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return conform(pd.DataFrame(columns=list(STANDING_DTYPES)), STANDING_DTYPES)
    curated = pd.DataFrame(
        {
            "driver": table["driverCode"],
            "name": table["familyName"],
            "nationality": table["driverNationality"],
            "team": table["constructorNames"].map(_last_team),
            "position": pd.to_numeric(table["position"], errors="coerce"),
            "points": pd.to_numeric(table["points"], errors="coerce"),
            "wins": pd.to_numeric(table["wins"], errors="coerce"),
        }
    )
    return conform(curated, STANDING_DTYPES)


def _last_team(names: Any) -> str | None:
    teams = list(names) if names is not None else []
    return str(teams[-1]) if teams else None


def _pages(response: Any) -> Iterator[Any]:
    while True:
        yield response
        try:
            response = response.get_next_result_page()
        except ValueError:
            return


def _frames(response: Any) -> Iterator[pd.DataFrame]:
    for page in _pages(response):
        yield pd.DataFrame(page)


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not frames:
        return conform(pd.DataFrame(columns=list(HISTORY_DTYPES)), HISTORY_DTYPES)
    return conform(pd.concat(frames, ignore_index=True), HISTORY_DTYPES)
