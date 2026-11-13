import pandas as pd
import pytest

from tests.factories import load_fastf1_race_sample
from vessel.curation import DRIVER_DTYPES, LAP_DTYPES, RESULT_DTYPES
from vessel.domain import SessionKind
from vessel.sources.fastf1_session import (
    FASTF1_SESSIONS,
    UNKNOWN_COMPOUND_COLOR,
    drivers_from_session,
    laps_from_session,
    results_from_session,
)

COMPOUND_COLORS = {"SOFT": "#da291c", "INTERMEDIATE": "#43b02a"}
TEAM_COLORS = {"McLaren": "#ff8000", "Audi": "#ff2d00"}
NATIONALITIES = {"NOR": "British", "BOR": "Brazilian"}


@pytest.fixture
def raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_fastf1_race_sample()


def lap(laps: pd.DataFrame, driver: str, number: int) -> pd.Series:
    return laps[(laps["driver"] == driver) & (laps["lap"] == number)].iloc[0]


def test_laps_are_curated_with_explicit_types(
    raw: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    laps = laps_from_session(raw[0], COMPOUND_COLORS)

    assert dict(laps.dtypes.astype(str)) == LAP_DTYPES
    assert lap(laps, "NOR", 15)["lap_time_s"] == pytest.approx(86.222)
    assert lap(laps, "NOR", 15)["compound_color"] == "#43b02a"


def test_pit_laps_become_flags(raw: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    laps = laps_from_session(raw[0], COMPOUND_COLORS)

    assert bool(lap(laps, "NOR", 16)["pit_in"])
    assert bool(lap(laps, "NOR", 17)["pit_out"])
    assert not bool(lap(laps, "NOR", 15)["pit_in"])


def test_unknown_compound_gets_neutral_color(
    raw: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    laps = laps_from_session(raw[0], {})

    assert set(laps["compound_color"]) == {UNKNOWN_COMPOUND_COLOR}


def test_results_keep_dnf_and_dns_unclassified(
    raw: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    results = results_from_session(raw[1], TEAM_COLORS, NATIONALITIES)

    assert dict(results.dtypes.astype(str)) == RESULT_DTYPES
    assert list(results["driver"]) == ["NOR", "BOR", "STR", "BOT"]
    assert list(results["classified"]) == [True, True, False, False]
    assert results.loc[results["driver"] == "BOR", "nationality"].item() == "Brazilian"
    assert results.loc[results["driver"] == "NOR", "team_color"].item() == "#ff8000"


def test_pit_lane_start_has_no_grid_slot(
    raw: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    raw_results = raw[1].copy()
    raw_results.loc[raw_results["Abbreviation"] == "BOR", "GridPosition"] = 0.0

    results = results_from_session(raw_results, TEAM_COLORS, NATIONALITIES)

    assert pd.isna(results.loc[results["driver"] == "BOR", "grid"].item())


def test_drivers_table_has_identity_without_race_columns(
    raw: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    drivers = drivers_from_session(raw[1], TEAM_COLORS, NATIONALITIES)

    assert dict(drivers.dtypes.astype(str)) == DRIVER_DTYPES
    bortoleto = drivers[drivers["driver"] == "BOR"].iloc[0]
    assert (bortoleto["name"], bortoleto["team_color"]) == ("Bortoleto", "#ff2d00")
    assert bortoleto["nationality"] == "Brazilian"


def test_every_session_kind_maps_to_fastf1() -> None:
    assert set(FASTF1_SESSIONS) == set(SessionKind)
