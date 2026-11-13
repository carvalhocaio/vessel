import pandas as pd
from matplotlib import patheffects
from matplotlib.ticker import FuncFormatter

from vessel.analytics.long_run import MIN_LONG_RUN_LAPS, team_ranking
from vessel.charts.canvas import Chart
from vessel.domain import ChartPreset, SessionKind
from vessel.formatting import (
    compound_name,
    format_lap_time,
    session_label,
    session_phrase,
)

LABEL_PT = 8
POINT_SIZE = 28
IQR_WIDTH = 5
IQR_ALPHA = 0.6
LABEL_GAP_RATIO = 0.015
LABEL_ROOM_RATIO = 0.45
LEFT_PAD_RATIO = 0.04
LABEL_HALO_WIDTH = 3


def long_run_chart(
    runs: pd.DataFrame, kind: SessionKind, preset: ChartPreset = ChartPreset.X
) -> Chart:
    leader = team_ranking(runs).iloc[0]
    chart = Chart(
        title=f"{leader['team']} tem o melhor ritmo {session_phrase(kind)}",
        subtitle=f"{session_label(kind)} · mediana e intervalo interquartil por "
        f"piloto · voltas limpas, mínimo de {MIN_LONG_RUN_LAPS}",
        preset=preset,
    )
    ax = chart.ax
    low, high = float(runs["q1_s"].min()), float(runs["q3_s"].max())
    span = max(high - low, 1.0)
    halo = [
        patheffects.withStroke(
            linewidth=LABEL_HALO_WIDTH, foreground=chart.theme.surface
        )
    ]
    for row, run in enumerate(runs.to_dict("records")):
        color = str(run["team_color"] or chart.theme.muted)
        ax.hlines(
            row,
            float(run["q1_s"]),
            float(run["q3_s"]),
            color=color,
            linewidth=IQR_WIDTH,
            alpha=IQR_ALPHA,
        )
        ax.scatter(float(run["median_s"]), row, s=POINT_SIZE, color=color, zorder=3)
        ax.text(
            float(run["q3_s"]) + span * LABEL_GAP_RATIO,
            row,
            _label(run),
            va="center",
            color=chart.theme.text_primary,
            fontsize=LABEL_PT,
            path_effects=halo,
        )
    ax.set_ylim(len(runs) - 0.5, -0.5)
    ax.set_yticks([])
    ax.set_xlim(low - span * LEFT_PAD_RATIO, high + span * LABEL_ROOM_RATIO)
    ax.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: format_lap_time(value, 1))
    )
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=chart.theme.grid, linewidth=0.8)
    ax.set_xlabel("Tempo de volta")
    return chart


def _label(run: dict[object, object]) -> str:
    compound = compound_name(str(run["compound"]))
    return f"{run['driver']} · {compound} · {run['laps']} voltas"
