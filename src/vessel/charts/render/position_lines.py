from vessel.charts.canvas import Chart
from vessel.charts.render.common import color_or_muted, halo
from vessel.domain import ChartPreset, PositionLinesSpec

DRIVER_LABEL_PT = 8
HIGHLIGHT_WIDTH = 2.4
RECESSIVE_WIDTH = 1.0
RECESSIVE_ALPHA = 0.35
LABEL_GAP_LAPS = 0.8
RIGHT_PAD_LAPS = 4
TICK_STEP = 5


def render_position_lines(spec: PositionLinesSpec, preset: ChartPreset) -> Chart:
    chart = Chart(spec.title, spec.subtitle, preset=preset)
    ax = chart.ax
    effects = halo(chart)
    for series in reversed(spec.series):
        color = color_or_muted(chart, series.color)
        bold = series.highlighted
        ax.plot(
            [point.lap for point in series.points],
            [point.position for point in series.points],
            color=color,
            linewidth=HIGHLIGHT_WIDTH if bold else RECESSIVE_WIDTH,
            alpha=1.0 if bold else RECESSIVE_ALPHA,
            linestyle="--" if series.dashed else "-",
            zorder=3 if bold else 2,
            solid_capstyle="round",
        )
        last = series.points[-1]
        ax.text(
            last.lap + LABEL_GAP_LAPS,
            last.position,
            series.end_label,
            va="center",
            color=chart.theme.text_primary if bold else chart.theme.muted,
            fontsize=DRIVER_LABEL_PT,
            fontweight="bold" if bold else "normal",
            clip_on=False,
            zorder=4,
            path_effects=effects,
        )
    field = int(spec.y.domain[1]) if spec.y.domain else len(spec.series)
    ax.set_ylim(field + 0.5, 0.5)
    ax.set_yticks([1, *range(TICK_STEP, field + 1, TICK_STEP)])
    last_lap = int(spec.x.domain[1]) if spec.x.domain else 0
    ax.set_xlim(0, last_lap + RIGHT_PAD_LAPS)
    ax.set_xlabel(spec.x.label or "")
    return chart
