from matplotlib import patheffects
from matplotlib.ticker import FuncFormatter

from vessel.charts.canvas import Chart
from vessel.domain import Axis, AxisFormat
from vessel.formatting import format_lap_time

LABEL_HALO_WIDTH = 3


def halo(chart: Chart) -> list[patheffects.AbstractPathEffect]:
    return [
        patheffects.withStroke(
            linewidth=LABEL_HALO_WIDTH, foreground=chart.theme.surface
        )
    ]


def color_or_muted(chart: Chart, color: str | None) -> str:
    return color or chart.theme.muted


def tick_formatter(axis: Axis) -> FuncFormatter | None:
    if axis.format is AxisFormat.LAP_TIME:
        return FuncFormatter(lambda value, _: format_lap_time(value, 1))
    if axis.format is AxisFormat.POSITION:
        return FuncFormatter(lambda value, _: f"P{int(value)}")
    return None


def vertical_grid(chart: Chart) -> None:
    chart.ax.grid(axis="y", visible=False)
    chart.ax.grid(axis="x", color=chart.theme.grid, linewidth=0.8)
