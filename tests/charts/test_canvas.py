from pathlib import Path

import pytest
from matplotlib.colors import to_rgb
from PIL import Image

from vessel.charts import (
    DARK,
    LIGHT,
    PRESET_SIZES_PX,
    Chart,
    Theme,
    credit_line,
    decimal_formatter,
)
from vessel.domain import ChartPreset, Source

HANDLE = "1caiocarvalho"


def test_credit_line_lists_sources_in_stable_order() -> None:
    line = credit_line([Source.JOLPICA, Source.FASTF1, Source.FASTF1], HANDLE)

    assert line == "Dados: FastF1 / Jolpica · @1caiocarvalho"


def test_credit_line_requires_a_source() -> None:
    with pytest.raises(ValueError, match="at least one"):
        credit_line([], HANDLE)


def test_decimal_formatter_uses_pt_br() -> None:
    assert decimal_formatter(2)(0.25, 0) == "0,25"


@pytest.mark.parametrize("preset", list(ChartPreset))
def test_save_renders_preset_size(tmp_path: Path, preset: ChartPreset) -> None:
    chart = Chart("Título", "Subtítulo", preset=preset)
    chart.ax.plot([1, 2, 3], [3, 1, 2])

    ref = chart.save(tmp_path, "long_run", [Source.FASTF1], HANDLE)

    with Image.open(tmp_path / ref.path) as image:
        assert image.size == PRESET_SIZES_PX[preset]


def test_save_returns_chart_ref_for_the_draft(tmp_path: Path) -> None:
    chart = Chart("Grid em Números")

    ref = chart.save(tmp_path, "grid", [Source.JOLPICA, Source.FASTF1], HANDLE)

    assert ref.path == "charts/grid_x.png"
    assert ref.preset is ChartPreset.X
    assert ref.sources == (Source.FASTF1, Source.JOLPICA)


def test_save_writes_credit_line_on_figure(tmp_path: Path) -> None:
    chart = Chart("Long Run")

    chart.save(tmp_path, "long_run", [Source.FASTF1], HANDLE)

    texts = [text.get_text() for text in chart.figure.texts]
    assert "Dados: FastF1 · @1caiocarvalho" in texts


@pytest.mark.parametrize("theme", [DARK, LIGHT])
def test_background_uses_theme_surface(tmp_path: Path, theme: Theme) -> None:
    chart = Chart("Tema", theme=theme)

    ref = chart.save(tmp_path, "theme", [Source.FASTF1], HANDLE)

    with Image.open(tmp_path / ref.path) as image:
        corner = image.convert("RGB").getpixel((2, 2))
    expected = tuple(round(channel * 255) for channel in to_rgb(theme.surface))
    assert corner == expected


@pytest.mark.parametrize("name", ["Long Run", "../escape", "", "1st"])
def test_save_rejects_unsafe_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(ValueError, match="invalid chart name"):
        Chart("x").save(tmp_path, name, [Source.FASTF1], HANDLE)
