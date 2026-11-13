from matplotlib.ticker import MaxNLocator

from vessel.charts.canvas import Chart
from vessel.charts.render.common import color_or_muted, halo, vertical_grid
from vessel.domain import ChartPreset, RankedDotsSpec

LABEL_PT = 9
BAR_HEIGHT = 0.62
LABEL_GAP = 0.15
X_ROOM_RATIO = 1.25


def render_ranked_dots(spec: RankedDotsSpec, preset: ChartPreset) -> Chart:
    chart = Chart(spec.title, spec.subtitle, preset=preset)
    ax = chart.ax
    effects = halo(chart)
    for row, series in enumerate(spec.series):
        value = series.point.value
        ax.barh(
            row,
            value,
            height=BAR_HEIGHT,
            color=color_or_muted(chart, series.color),
        )
        ax.text(
            value + LABEL_GAP,
            row,
            series.detail_label,
            va="center",
            color=chart.theme.text_primary,
            fontsize=LABEL_PT,
            path_effects=effects,
        )
    worst = max(series.point.value for series in spec.series)
    ax.set_ylim(len(spec.series) - 0.5, -0.5)
    ax.set_yticks([])
    ax.set_xlim(0, worst * X_ROOM_RATIO + 1)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    vertical_grid(chart)
    ax.set_xlabel(spec.x.label or "")
    return chart
