from collections.abc import Sequence

import pandas as pd
import pytest

from vessel.analytics.long_run import (
    MIN_LONG_RUN_LAPS,
    NoLongRunError,
    degradation,
    long_run_facts,
    long_run_laps,
    long_runs,
    team_ranking,
)
from vessel.curation import DRIVER_DTYPES, LAP_DTYPES, SessionTables, conform
from vessel.domain import Fact, Source

BASE = 90.0


def stint_laps(
    driver: str,
    times: Sequence[float],
    *,
    compound: str = "MEDIUM",
    first_lap: int = 2,
    stint: int = 1,
    tyre_start: int = 2,
) -> pd.DataFrame:
    count = len(times)
    return pd.DataFrame(
        {
            "driver": driver,
            "team": f"Team {driver}",
            "lap": range(first_lap, first_lap + count),
            "lap_time_s": list(times),
            "stint": stint,
            "compound": compound,
            "compound_color": "#ffffff",
            "tyre_life": range(tyre_start, tyre_start + count),
            "position": pd.NA,
            "pit_in": False,
            "pit_out": False,
            "track_status": "1",
            "is_accurate": True,
        }
    )


def laps_of(*frames: pd.DataFrame) -> pd.DataFrame:
    return conform(pd.concat(frames, ignore_index=True), LAP_DTYPES)


def drivers_of(*rows: tuple[str, str, str]) -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "driver": driver,
                "name": driver.title(),
                "team": team,
                "team_color": "#ff8000",
                "nationality": nationality,
            }
            for driver, team, nationality in rows
        ]
    )
    return conform(frame, DRIVER_DTYPES)


def facts_by_key(runs: pd.DataFrame) -> dict[str, Fact]:
    return {fact.key: fact for fact in long_run_facts(runs, Source.FASTF1)}


def test_detects_long_runs_in_recorded_fp2(fp2_2026_20: SessionTables) -> None:
    runs = long_runs(fp2_2026_20.laps, fp2_2026_20.drivers)

    assert len(runs) == 21
    assert (runs["laps"] >= MIN_LONG_RUN_LAPS).all()
    assert runs["median_s"].is_monotonic_increasing
    assert list(runs["rank"]) == list(range(1, 22))
    leader = runs.iloc[0]
    assert (leader["driver"], leader["compound"], leader["laps"]) == ("ANT", "SOFT", 17)
    assert leader["median_s"] == pytest.approx(75.404, abs=0.001)


def test_detects_long_runs_in_recorded_sprint(sprint_2026_17: SessionTables) -> None:
    runs = long_runs(sprint_2026_17.laps, sprint_2026_17.drivers)

    assert runs.iloc[0]["driver"] == "VER"
    assert runs.iloc[0]["laps"] == 14
    assert set(runs["compound"]) == {"INTERMEDIATE"}
    assert not {"BOR", "CAM", "STR"} & set(runs["driver"])
    assert "BOR" not in set(runs["driver"])


def test_sequence_breaks_on_lap_that_is_not_clean() -> None:
    first = stint_laps("NOR", [BASE] * 4)
    pit_in = stint_laps("NOR", [BASE], first_lap=6, tyre_start=6).assign(pit_in=True)
    second = stint_laps("NOR", [BASE] * 5, first_lap=7, tyre_start=7)

    assert long_run_laps(laps_of(first, pit_in, second)).empty


def test_long_run_needs_minimum_laps() -> None:
    short = stint_laps("NOR", [BASE] * (MIN_LONG_RUN_LAPS - 1))
    enough = stint_laps("PIA", [BASE] * MIN_LONG_RUN_LAPS)

    selected = long_run_laps(laps_of(short, enough))

    assert set(selected["driver"]) == {"PIA"}


def test_drops_laps_above_107_percent_of_stint_median() -> None:
    times = [BASE] * 7 + [BASE * 1.08]

    selected = long_run_laps(laps_of(stint_laps("NOR", times)))

    assert len(selected) == 7
    assert selected["lap_time_s"].max() == BASE


def test_keeps_the_longest_run_per_driver() -> None:
    short = stint_laps("NOR", [BASE] * 6, stint=1)
    long = stint_laps("NOR", [BASE + 1] * 9, first_lap=12, stint=2, tyre_start=1)

    selected = long_run_laps(laps_of(short, long))

    assert len(selected) == 9
    assert set(selected["stint"]) == {2}


def test_degradation_is_slope_of_lap_time_by_tyre_life() -> None:
    times = [BASE + 0.1 * index for index in range(8)]

    run = laps_of(stint_laps("NOR", times))

    assert degradation(run) == pytest.approx(0.1)


def test_degradation_needs_tyre_life() -> None:
    run = laps_of(stint_laps("NOR", [BASE] * 6))
    run["tyre_life"] = pd.Series([pd.NA] * len(run), dtype="Int16")

    assert degradation(run) is None


def test_team_ranking_keeps_best_run_per_team() -> None:
    laps = laps_of(
        stint_laps("NOR", [BASE] * 6),
        stint_laps("PIA", [BASE + 0.5] * 6),
        stint_laps("LEC", [BASE + 0.2] * 6),
    )
    drivers = drivers_of(
        ("NOR", "McLaren", "British"),
        ("PIA", "McLaren", "Australian"),
        ("LEC", "Ferrari", "Monegasque"),
    )

    ranking = team_ranking(long_runs(laps, drivers))

    assert list(ranking["team"]) == ["McLaren", "Ferrari"]
    assert list(ranking["driver"]) == ["NOR", "LEC"]


def test_pace_gap_compares_same_compound() -> None:
    laps = laps_of(
        stint_laps("NOR", [BASE] * 6, compound="MEDIUM"),
        stint_laps("LEC", [BASE + 0.1] * 6, compound="HARD"),
        stint_laps("RUS", [BASE + 0.3] * 6, compound="MEDIUM"),
    )
    drivers = drivers_of(
        ("NOR", "McLaren", "British"),
        ("LEC", "Ferrari", "Monegasque"),
        ("RUS", "Mercedes", "British"),
    )

    fact = facts_by_key(long_runs(laps, drivers))["top_teams_pace_gap"]

    assert fact.value == pytest.approx(0.3)
    assert "Mercedes" in fact.context
    assert "Ferrari foi a 2ª no ranking geral, mas com pneu duro" in fact.context


def test_compound_mismatch_does_not_compare_pace() -> None:
    laps = laps_of(
        stint_laps("NOR", [BASE] * 6, compound="MEDIUM"),
        stint_laps("LEC", [BASE + 0.1] * 6, compound="HARD"),
    )
    drivers = drivers_of(
        ("NOR", "McLaren", "British"), ("LEC", "Ferrari", "Monegasque")
    )

    facts = facts_by_key(long_runs(laps, drivers))

    assert "top_teams_pace_gap" not in facts
    mismatch = facts["top_teams_compound_mismatch"]
    assert mismatch.value == "médio vs duro"
    assert "compostos diferentes" in mismatch.context


def test_facts_from_recorded_fp2(fp2_2026_20: SessionTables) -> None:
    facts = facts_by_key(long_runs(fp2_2026_20.laps, fp2_2026_20.drivers))

    assert set(facts) == {
        "top_teams_pace_gap",
        "highest_degradation",
        "lowest_degradation",
        "longest_long_run",
        "best_brazilian_rank",
    }
    assert facts["top_teams_pace_gap"].value == pytest.approx(0.143, abs=0.001)
    assert facts["highest_degradation"].value == pytest.approx(0.233, abs=0.001)
    assert facts["lowest_degradation"].display == "-0,035 s/volta"
    assert facts["longest_long_run"].value == 17
    assert facts["best_brazilian_rank"].value == 10
    assert "Bortoleto" in facts["best_brazilian_rank"].context


def test_brazilian_rank_is_omitted_without_brazilian_long_run(
    sprint_2026_17: SessionTables,
) -> None:
    facts = facts_by_key(long_runs(sprint_2026_17.laps, sprint_2026_17.drivers))

    assert "best_brazilian_rank" not in facts
    assert "top_teams_pace_gap" in facts


def test_no_long_run_raises() -> None:
    laps = laps_of(stint_laps("NOR", [BASE] * 3))

    runs = long_runs(laps, drivers_of(("NOR", "McLaren", "British")))

    with pytest.raises(NoLongRunError):
        long_run_facts(runs, Source.FASTF1)
