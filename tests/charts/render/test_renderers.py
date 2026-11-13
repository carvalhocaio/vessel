import json
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from vessel.analytics.form import recent_form
from vessel.analytics.long_run import long_runs
from vessel.analytics.race import positions_by_lap, stint_summary
from vessel.charts import PRESET_SIZES_PX
from vessel.charts.output import load_spec, save_chart
from vessel.charts.specs.circuit_preview import grid_timeline_spec, ranked_dots_spec
from vessel.charts.specs.long_run import ranged_dots_spec
from vessel.charts.specs.race import position_lines_spec, stint_bars_spec
from vessel.curation import RaceTables, SeasonTables, SessionTables
from vessel.domain import ChartPreset, ChartSpec, SessionKind

HANDLE = "1caiocarvalho"


@pytest.fixture
def specs(
    race_2026_20: RaceTables,
    sprint_2026_17: SessionTables,
    interlagos_history: pd.DataFrame,
    season_2026: SeasonTables,
) -> dict[str, ChartSpec]:
    laps, results = race_2026_20.laps, race_2026_20.results
    return {
        "stints": stint_bars_spec(stint_summary(laps), laps, results),
        "positions": position_lines_spec(
            positions_by_lap(laps, results), laps, results
        ),
        "long_run": ranged_dots_spec(
            long_runs(sprint_2026_17.laps, sprint_2026_17.drivers), SessionKind.SPRINT
        ),
        "winners": grid_timeline_spec(interlagos_history, "São Paulo"),
        "form": ranked_dots_spec(
            recent_form(season_2026.results), season_2026.standings, {}
        ),
    }


@pytest.mark.parametrize("preset", list(ChartPreset))
def test_every_kind_renders_the_preset_size(
    tmp_path: Path, specs: dict[str, ChartSpec], preset: ChartPreset
) -> None:
    for name, spec in specs.items():
        ref = save_chart(spec, tmp_path, name, HANDLE, preset)

        with Image.open(tmp_path / ref.path) as image:
            assert image.size == PRESET_SIZES_PX[preset]


def test_save_chart_writes_spec_next_to_png(
    tmp_path: Path, specs: dict[str, ChartSpec]
) -> None:
    ref = save_chart(specs["positions"], tmp_path, "positions", HANDLE)

    assert ref.path == "charts/positions_x.png"
    assert ref.spec_path == "charts/positions.json"
    assert ref.sources == specs["positions"].sources
    assert load_spec(tmp_path / ref.spec_path) == specs["positions"]
    document = json.loads((tmp_path / ref.spec_path).read_text(encoding="utf-8"))
    assert document["kind"] == "position_lines"
