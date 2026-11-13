from vessel.charts.canvas import Chart
from vessel.charts.render.common import color_or_muted, vertical_grid
from vessel.domain import ChartPreset, StintBarsSpec

DRIVER_LABEL_PT = 8
COMPOUND_LABEL_PT = 7
MIN_LAPS_FOR_LETTER = 4
BAR_HEIGHT = 0.72


def render_stint_bars(spec: StintBarsSpec, preset: ChartPreset) -> Chart:
    chart = Chart(spec.title, spec.subtitle, preset=preset)
    ax = chart.ax
    for row, series in enumerate(spec.series):
        for segment in series.segments:
            start = segment.start_lap - 1
            ax.barh(
                row,
                width=segment.laps,
                left=start,
                height=BAR_HEIGHT,
                color=color_or_muted(chart, segment.color),
                edgecolor=chart.theme.surface,
                linewidth=0.8,
            )
            if segment.laps >= MIN_LAPS_FOR_LETTER:
                ax.text(
                    start + segment.laps / 2,
                    row,
                    segment.category_label,
                    ha="center",
                    va="center",
                    color=chart.theme.surface,
                    fontsize=COMPOUND_LABEL_PT,
                    fontweight="bold",
                )
    labels = [series.label for series in spec.series]
    ax.set_yticks(range(len(labels)), labels=labels, fontsize=DRIVER_LABEL_PT)
    ax.set_ylim(len(labels) - 0.5, -0.5)
    if spec.x.domain is not None:
        ax.set_xlim(*spec.x.domain)
    vertical_grid(chart)
    return chart
