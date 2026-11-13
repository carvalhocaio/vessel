import pandas as pd

from tests.factories import FIXTURES
from vessel.curation import HISTORY_DTYPES, STANDING_DTYPES
from vessel.sources.jolpica import results_from_ergast, standings_from_ergast


def test_race_results_are_curated_with_explicit_types() -> None:
    description = pd.read_parquet(FIXTURES / "jolpica_2025_22_description.parquet")
    results = pd.read_parquet(FIXTURES / "jolpica_2025_22_results.parquet")

    curated = results_from_ergast(description, [results], "race")

    assert dict(curated.dtypes.astype(str)) == HISTORY_DTYPES
    winner = curated.iloc[0]
    assert (winner["season"], winner["round"], winner["circuit_id"]) == (
        2025,
        22,
        "vegas",
    )
    assert (winner["driver"], winner["grid"], winner["finish"]) == ("VER", 2, 1)
    assert winner["date"] == "2025-11-23"
    assert winner["session"] == "race"


def test_empty_result_pages_are_skipped() -> None:
    description = pd.read_parquet(FIXTURES / "jolpica_2025_22_description.parquet")

    curated = results_from_ergast(description, [pd.DataFrame()], "race")

    assert curated.empty
    assert list(curated.columns) == list(HISTORY_DTYPES)


def test_standings_keep_the_latest_team() -> None:
    table = pd.read_parquet(FIXTURES / "jolpica_2026_standings.parquet")

    standings = standings_from_ergast(table)

    assert dict(standings.dtypes.astype(str)) == STANDING_DTYPES
    leader = standings.iloc[0]
    assert (leader["driver"], leader["team"], leader["points"]) == (
        "ANT",
        "Mercedes",
        390,
    )
