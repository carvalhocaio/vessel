from matplotlib.ticker import MaxNLocator

from vessel.charts.canvas import Chart
from vessel.charts.render.common import halo, tick_formatter
from vessel.domain import ChartPreset, GridTimelineSpec

LABEL_PT = 9
POINT_SIZE = 60
LABEL_OFFSET = 0.35
X_PAD_YEARS = 0.8
MIN_DEPTH = 3
DENSE_TICKS = 10


def render_grid_timeline(spec: GridTimelineSpec, preset: ChartPreset) -> Chart:
    chart = Chart(spec.title, spec.subtitle, preset=preset)
    ax = chart.ax
    effects = halo(chart)
    points = [point for series in spec.series for point in series.points]
    years = [point.season for point in points]
    starts = [point.start for point in points]
    ax.scatter(years, starts, s=POINT_SIZE, color=chart.theme.categorical[0], zorder=3)
    for point in points:
        ax.text(
            point.season,
            point.start - LABEL_OFFSET,
            point.label,
            ha="center",
            va="bottom",
            color=chart.theme.text_primary,
            fontsize=LABEL_PT,
            fontweight="bold",
            path_effects=effects,
        )
    deepest = max(*starts, MIN_DEPTH)
    step = 1 if deepest <= DENSE_TICKS else 2
    ax.set_ylim(deepest + 1, 0)
    ax.set_yticks(range(1, deepest + 1, step))
    if (formatter := tick_formatter(spec.y)) is not None:
        ax.yaxis.set_major_formatter(formatter)
    ax.set_xlim(min(years) - X_PAD_YEARS, max(years) + X_PAD_YEARS)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    return chart
