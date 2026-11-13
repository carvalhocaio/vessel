from pathlib import Path

from PIL import Image

from vessel.analytics.long_run import long_runs
from vessel.charts import PRESET_SIZES_PX
from vessel.charts.long_run import long_run_chart
from vessel.curation import SessionTables
from vessel.domain import ChartPreset, SessionKind, Source


def test_long_run_chart_labels_driver_compound_and_laps(
    tmp_path: Path, fp2_2026_20: SessionTables
) -> None:
    runs = long_runs(fp2_2026_20.laps, fp2_2026_20.drivers)
    chart = long_run_chart(runs, SessionKind.PRACTICE_2)

    ref = chart.save(tmp_path, "long_run", [Source.FASTF1], "1caiocarvalho")

    with Image.open(tmp_path / ref.path) as image:
        assert image.size == PRESET_SIZES_PX[ChartPreset.X]
    labels = [text.get_text() for text in chart.ax.texts]
    assert labels[0] == "ANT · macio · 17 voltas"
    assert len(labels) == len(runs)
    figure_texts = [text.get_text() for text in chart.figure.texts]
    assert "Mercedes tem o melhor ritmo no TL2" in figure_texts
    assert any("voltas limpas, mínimo de 6" in text for text in figure_texts)


def test_sprint_title_uses_feminine_article(sprint_2026_17: SessionTables) -> None:
    runs = long_runs(sprint_2026_17.laps, sprint_2026_17.drivers)

    chart = long_run_chart(runs, SessionKind.SPRINT)

    titles = [text.get_text() for text in chart.figure.texts]
    assert "Red Bull Racing tem o melhor ritmo na Sprint" in titles
