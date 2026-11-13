import pandas as pd

from vessel.analytics.circuit_history import circuit_facts, editions, winners
from vessel.analytics.form import current_grid
from vessel.curation import SeasonTables
from vessel.domain import Fact, Source


def facts_by_key(
    history: pd.DataFrame, season: SeasonTables, location: str
) -> dict[str, Fact]:
    grid = current_grid(season.results)
    facts = circuit_facts(history, grid, location, Source.JOLPICA)
    return {fact.key: fact for fact in facts}


def test_interlagos_window_skips_seasons_without_a_race(
    interlagos_history: pd.DataFrame,
) -> None:
    assert editions(interlagos_history) == 10
    assert 2020 not in set(interlagos_history["season"])
    assert interlagos_history["season"].max() == 2025


def test_interlagos_winners_by_year(interlagos_history: pd.DataFrame) -> None:
    won = winners(interlagos_history).set_index("season")

    assert won.loc[2024, "driver"] == "VER"
    assert won.loc[2024, "start"] == 17
    assert won.loc[2025, "driver"] == "NOR"


def test_interlagos_facts(
    interlagos_history: pd.DataFrame, season_2026: SeasonTables
) -> None:
    facts = facts_by_key(interlagos_history, season_2026, "São Paulo")

    assert facts["circuit_pole_to_win"].display == "70% (7 de 10)"
    assert facts["circuit_furthest_back_winner"].value == 17
    assert "Verstappen" in facts["circuit_furthest_back_winner"].context
    assert facts["circuit_top_current_driver"].value == 3
    assert "Hamilton" in facts["circuit_top_current_driver"].context
    assert "Verstappen" in facts["circuit_top_current_driver"].context
    assert facts["circuit_team_wins"].display == "Mercedes: 5 de 10"
    assert facts["circuit_best_brazilian"].value == 7
    assert "Massa" in facts["circuit_best_brazilian"].context


def test_las_vegas_facts(
    vegas_history: pd.DataFrame, season_2026: SeasonTables
) -> None:
    facts = facts_by_key(vegas_history, season_2026, "Las Vegas")

    assert editions(vegas_history) == 3
    assert facts["circuit_last_winner"].display == "Verstappen (2025)"
    assert facts["circuit_pole_to_win"].display == "33% (1 de 3)"
    assert facts["circuit_best_brazilian"].display == "P17 (Bortoleto, 2025)"
    assert "circuit_first_race" not in facts


def test_circuit_without_history_is_a_first_race(
    madring_history: pd.DataFrame, season_2026: SeasonTables
) -> None:
    facts = facts_by_key(madring_history, season_2026, "Madrid")

    assert list(facts) == ["circuit_first_race"]
    assert facts["circuit_first_race"].display == "Estreia em Madrid"


def test_pit_lane_winner_counts_as_back_of_grid(
    vegas_history: pd.DataFrame, season_2026: SeasonTables
) -> None:
    history = vegas_history.copy()
    winner_2024 = (history["season"] == 2024) & (history["finish"] == 1)
    history.loc[winner_2024, "grid"] = 0

    facts = facts_by_key(history, season_2026, "Las Vegas")

    assert facts["circuit_furthest_back_winner"].display == "pit lane"
    assert "pit lane" in facts["circuit_furthest_back_winner"].context


def test_best_brazilian_is_omitted_without_brazilians(
    vegas_history: pd.DataFrame, season_2026: SeasonTables
) -> None:
    history = vegas_history[vegas_history["nationality"] != "Brazilian"]

    facts = facts_by_key(history, season_2026, "Las Vegas")

    assert "circuit_best_brazilian" not in facts
