import pandas as pd
import pytest

from tests.factories import facts_for
from vessel.analytics.race import (
    RACE_FACTS,
    classified,
    clean_laps,
    finishing_order,
    highlighted_drivers,
    positions_by_lap,
    stint_summary,
)
from vessel.analytics.registry import CalcInputs
from vessel.curation import RaceTables
from vessel.domain import Fact, Source


def facts_by_key(tables: RaceTables) -> dict[str, Fact]:
    return facts_for(RACE_FACTS, CalcInputs(race_tables=tables))


def test_clean_laps_drop_first_lap_pit_laps_and_neutralised_laps(
    race_2026_20: RaceTables,
) -> None:
    clean = clean_laps(race_2026_20.laps)

    norris = clean[clean["driver"] == "NOR"]
    assert len(norris) == 64
    assert not clean["pit_in"].any()
    assert not clean["pit_out"].any()
    assert (clean["lap"] > 1).all()


def test_clean_laps_exclude_safety_car_and_vsc() -> None:
    laps = pd.DataFrame(
        {
            "lap": [2, 3, 4, 5],
            "lap_time_s": [80.0, 81.0, 82.0, 83.0],
            "is_accurate": [True] * 4,
            "pit_in": [False] * 4,
            "pit_out": [False] * 4,
            "track_status": ["1", "14", "6", "12"],
        }
    )

    assert list(clean_laps(laps)["lap"]) == [2, 5]


def test_stint_summary_for_winner(race_2026_20: RaceTables) -> None:
    stints = stint_summary(race_2026_20.laps)

    norris = stints[stints["driver"] == "NOR"]
    assert list(norris["compound"]) == ["INTERMEDIATE", "SOFT", "SOFT", "INTERMEDIATE"]
    assert list(norris["laps"]) == [16, 33, 13, 9]
    assert norris["laps"].sum() == 71


def test_positions_start_from_grid_and_skip_non_starters(
    race_2026_20: RaceTables,
) -> None:
    positions = positions_by_lap(race_2026_20.laps, race_2026_20.results)

    grid = positions[positions["lap"] == 0].set_index("driver")["position"]
    assert grid["VER"] == 21
    assert "BOT" not in set(positions["driver"])
    assert positions.loc[positions["driver"] == "STR", "lap"].max() < 71


def test_retirements_do_not_break_ranking(race_2026_20: RaceTables) -> None:
    order = finishing_order(race_2026_20.results, race_2026_20.laps)
    ranked = classified(race_2026_20.results, race_2026_20.laps)

    assert order[0] == "NOR"
    assert order[-1] == "STR"
    assert "BOT" not in order
    assert [entry.finish for entry in ranked] == list(range(1, 21))


def test_race_facts_from_recorded_race(race_2026_20: RaceTables) -> None:
    facts = facts_by_key(race_2026_20)

    assert set(facts) == {
        "biggest_gain",
        "biggest_loss",
        "longest_stint",
        "fastest_lap",
        "winner_pace_gap_p2",
        "winner_pit_stops",
    }
    assert facts["biggest_gain"].value == 19
    assert "Verstappen" in facts["biggest_gain"].context
    assert facts["biggest_loss"].value == -11
    assert "Bearman" in facts["biggest_loss"].context
    assert facts["longest_stint"].value == 45
    assert "Russell" in facts["longest_stint"].context
    assert facts["fastest_lap"].display == "1:12,689"
    assert "Antonelli" in facts["fastest_lap"].context
    assert facts["winner_pace_gap_p2"].value == pytest.approx(0.587, abs=0.001)
    assert facts["winner_pace_gap_p2"].display == "0,587 s/volta"
    assert facts["winner_pit_stops"].value == 3
    assert all(fact.source is Source.FASTF1 for fact in facts.values())


def test_pace_gap_is_omitted_without_clean_laps_for_p2(
    race_2026_20: RaceTables,
) -> None:
    laps = race_2026_20.laps.copy()
    laps.loc[laps["driver"] == "VER", "is_accurate"] = False

    facts = facts_by_key(RaceTables(laps, race_2026_20.results))

    assert "winner_pace_gap_p2" not in facts


def test_pit_lane_start_counts_as_back_of_grid(race_2026_20: RaceTables) -> None:
    results = race_2026_20.results.copy()
    results.loc[results["driver"] == "VER", "grid"] = pd.NA

    facts = facts_by_key(RaceTables(race_2026_20.laps, results))

    assert facts["biggest_gain"].value == 19
    assert "pit lane" in facts["biggest_gain"].context


def test_gain_ties_break_by_better_finish(race_2026_20: RaceTables) -> None:
    results = race_2026_20.results.copy()
    results.loc[results["driver"] == "VER", "grid"] = 13

    facts = facts_by_key(RaceTables(race_2026_20.laps, results))

    assert facts["biggest_gain"].value == 11
    assert "Verstappen" in facts["biggest_gain"].context


def test_highlights_podium_and_brazilians(race_2026_20: RaceTables) -> None:
    assert highlighted_drivers(race_2026_20.results) == {
        "NOR",
        "VER",
        "HAD",
        "BOR",
        "CAM",
    }
