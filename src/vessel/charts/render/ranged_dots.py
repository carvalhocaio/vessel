from vessel.charts.canvas import Chart
from vessel.charts.render.common import (
    color_or_muted,
    halo,
    tick_formatter,
    vertical_grid,
)
from vessel.domain import ChartPreset, RangedDotsSpec

LABEL_PT = 8
POINT_SIZE = 28
IQR_WIDTH = 5
IQR_ALPHA = 0.6
LABEL_GAP_RATIO = 0.015
LABEL_ROOM_RATIO = 0.45
LEFT_PAD_RATIO = 0.04
MIN_SPAN = 1.0


def render_ranged_dots(spec: RangedDotsSpec, preset: ChartPreset) -> Chart:
    chart = Chart(spec.title, spec.subtitle, preset=preset)
    ax = chart.ax
    low = min(series.point.low for series in spec.series)
    high = max(series.point.high for series in spec.series)
    span = max(high - low, MIN_SPAN)
    effects = halo(chart)
    for row, series in enumerate(spec.series):
        color = color_or_muted(chart, series.color)
        point = series.point
        ax.hlines(
            row,
            point.low,
            point.high,
            color=color,
            linewidth=IQR_WIDTH,
            alpha=IQR_ALPHA,
        )
        ax.scatter(point.value, row, s=POINT_SIZE, color=color, zorder=3)
        ax.text(
            point.high + span * LABEL_GAP_RATIO,
            row,
            series.detail_label,
            va="center",
            color=chart.theme.text_primary,
            fontsize=LABEL_PT,
            path_effects=effects,
        )
    ax.set_ylim(len(spec.series) - 0.5, -0.5)
    ax.set_yticks([])
    ax.set_xlim(low - span * LEFT_PAD_RATIO, high + span * LABEL_ROOM_RATIO)
    if (formatter := tick_formatter(spec.x)) is not None:
        ax.xaxis.set_major_formatter(formatter)
    vertical_grid(chart)
    ax.set_xlabel(spec.x.label or "")
    return chart
