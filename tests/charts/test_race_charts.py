from pathlib import Path

from PIL import Image

from vessel.analytics.race import positions_by_lap, stint_summary
from vessel.charts import PRESET_SIZES_PX
from vessel.charts.race import position_chart, stint_chart
from vessel.curation import RaceTables
from vessel.domain import ChartPreset, Source

HANDLE = "1caiocarvalho"


def test_stint_chart_renders_x_preset(tmp_path: Path, race_2026_20: RaceTables) -> None:
    laps, results = race_2026_20.laps, race_2026_20.results
    chart = stint_chart(stint_summary(laps), laps, results)

    ref = chart.save(tmp_path, "stints", [Source.FASTF1], HANDLE)

    with Image.open(tmp_path / ref.path) as image:
        assert image.size == PRESET_SIZES_PX[ChartPreset.X]
    texts = [text.get_text() for text in chart.figure.texts]
    assert "Norris venceu com 3 paradas" in texts
    assert any("INT intermediário" in text for text in texts)


def test_position_chart_labels_every_starter(
    tmp_path: Path, race_2026_20: RaceTables
) -> None:
    laps, results = race_2026_20.laps, race_2026_20.results
    chart = position_chart(positions_by_lap(laps, results), laps, results)

    ref = chart.save(tmp_path, "positions", [Source.FASTF1], HANDLE)

    with Image.open(tmp_path / ref.path) as image:
        assert image.size == PRESET_SIZES_PX[ChartPreset.X]
    labels = {text.get_text() for text in chart.ax.texts}
    assert {"NOR", "BOR", "CAM", "STR"} <= labels
    assert "BOT" not in labels
    assert "Norris largou na pole e venceu" in [
        t.get_text() for t in chart.figure.texts
    ]
