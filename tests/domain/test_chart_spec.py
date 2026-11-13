import json

import pandas as pd
import pytest
from pydantic import ValidationError

from vessel.analytics.form import recent_form
from vessel.analytics.long_run import long_runs
from vessel.analytics.race import positions_by_lap, stint_summary
from vessel.charts.specs.circuit_preview import grid_timeline_spec, ranked_dots_spec
from vessel.charts.specs.long_run import ranged_dots_spec
from vessel.charts.specs.race import position_lines_spec, stint_bars_spec
from vessel.curation import RaceTables, SeasonTables, SessionTables
from vessel.domain import CHART_SPEC, ChartSpec, SessionKind


@pytest.fixture
def specs(
    race_2026_20: RaceTables,
    fp2_2026_20: SessionTables,
    vegas_history: pd.DataFrame,
    season_2026: SeasonTables,
) -> list[ChartSpec]:
    laps, results = race_2026_20.laps, race_2026_20.results
    return [
        stint_bars_spec(stint_summary(laps), laps, results),
        position_lines_spec(positions_by_lap(laps, results), laps, results),
        ranged_dots_spec(
            long_runs(fp2_2026_20.laps, fp2_2026_20.drivers), SessionKind.PRACTICE_2
        ),
        grid_timeline_spec(vegas_history, "Las Vegas"),
        ranked_dots_spec(recent_form(season_2026.results), season_2026.standings, {}),
    ]


def test_every_kind_round_trips_through_json(specs: list[ChartSpec]) -> None:
    for spec in specs:
        restored = CHART_SPEC.validate_json(CHART_SPEC.dump_json(spec))

        assert restored == spec
        assert type(restored) is type(spec)


def test_kinds_cover_the_five_charts(specs: list[ChartSpec]) -> None:
    assert [spec.kind for spec in specs] == [
        "stint_bars",
        "position_lines",
        "ranged_dots",
        "grid_timeline",
        "ranked_dots",
    ]


def test_unknown_kind_is_rejected(specs: list[ChartSpec]) -> None:
    document = json.loads(CHART_SPEC.dump_json(specs[0]))
    document["kind"] = "pie"

    with pytest.raises(ValidationError):
        CHART_SPEC.validate_python(document)


def test_extra_fields_are_rejected(specs: list[ChartSpec]) -> None:
    document = json.loads(CHART_SPEC.dump_json(specs[3]))
    document["color_scheme"] = "neon"

    with pytest.raises(ValidationError):
        CHART_SPEC.validate_python(document)
