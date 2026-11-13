import pytest

from vessel.analytics.circuit_history import CIRCUIT_FACTS
from vessel.analytics.form import CHAMPIONSHIP_FACTS, FORM_FACTS
from vessel.analytics.long_run import LONG_RUN_FACTS
from vessel.analytics.race import RACE_FACTS
from vessel.analytics.registry import (
    CHARTS,
    FACTS,
    CalcInputs,
    CalculationError,
    MissingInputError,
    calculation,
    chart_entry,
    fact_entry,
    float_param,
    int_param,
)
from vessel.calculations import load_calculations
from vessel.domain import ParamValue, Source


def test_every_key_used_by_reports_is_registered() -> None:
    load_calculations()
    used = RACE_FACTS + LONG_RUN_FACTS + CIRCUIT_FACTS + FORM_FACTS + CHAMPIONSHIP_FACTS

    assert set(used) <= set(FACTS)
    assert set(CHARTS) == {
        "chart.stints",
        "chart.positions",
        "chart.long_run",
        "chart.winners",
        "chart.form",
    }


def test_duplicate_key_is_an_error() -> None:
    with pytest.raises(CalculationError, match="already registered"):
        calculation("race.biggest_gain", Source.FASTF1)(lambda inputs, params: None)


def test_unknown_keys_are_errors() -> None:
    with pytest.raises(CalculationError, match="not registered"):
        fact_entry("race.made_up")
    with pytest.raises(CalculationError, match="not registered"):
        chart_entry("chart.made_up")


def test_missing_table_is_reported_by_name() -> None:
    with pytest.raises(MissingInputError, match="race session tables"):
        fact_entry("race.biggest_gain").compute(CalcInputs(), {})


def test_parameters_are_type_checked() -> None:
    params: dict[str, ParamValue] = {
        "min_laps": 6,
        "outlier_ratio": 1.07,
        "location": "Las Vegas",
    }

    assert int_param(params, "min_laps") == 6
    assert float_param(params, "outlier_ratio") == 1.07
    with pytest.raises(CalculationError, match="must be an integer"):
        int_param(params, "location")
    with pytest.raises(CalculationError, match="missing parameter 'editions'"):
        int_param(params, "editions")
