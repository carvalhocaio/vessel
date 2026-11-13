from collections.abc import Mapping

import pandas as pd
from matplotlib import patheffects
from matplotlib.ticker import FuncFormatter, MaxNLocator

from vessel.analytics.circuit_history import winners
from vessel.charts.canvas import Chart
from vessel.domain import ChartPreset
from vessel.formatting import format_decimal

LABEL_PT = 9
POINT_SIZE = 60
LABEL_OFFSET = 0.35
BAR_HEIGHT = 0.62
LABEL_HALO_WIDTH = 3
FORM_TOP = 10
X_PAD_YEARS = 0.8
MIN_DEPTH = 3
DENSE_TICKS = 10
LABEL_GAP = 0.15


def winners_chart(
    history: pd.DataFrame, location: str, preset: ChartPreset = ChartPreset.X
) -> Chart:
    won = winners(history)
    total, poles = len(won), int((won["grid"] == 1).sum())
    chart = Chart(
        title=_winners_title(poles, total, location),
        subtitle=f"Posição de largada do vencedor em cada edição · {location}",
        preset=preset,
    )
    ax = chart.ax
    halo = _halo(chart)
    years = won["season"].astype(int)
    starts = won["start"].astype(int)
    ax.scatter(years, starts, s=POINT_SIZE, color=chart.theme.categorical[0], zorder=3)
    for row in won.to_dict("records"):
        ax.text(
            int(row["season"]),
            int(row["start"]) - LABEL_OFFSET,
            str(row["driver"]),
            ha="center",
            va="bottom",
            color=chart.theme.text_primary,
            fontsize=LABEL_PT,
            fontweight="bold",
            path_effects=halo,
        )
    deepest = max(int(starts.max()), MIN_DEPTH)
    step = 1 if deepest <= DENSE_TICKS else 2
    ax.set_ylim(deepest + 1, 0)
    ax.set_yticks(range(1, deepest + 1, step))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"P{int(value)}"))
    ax.set_xlim(years.min() - X_PAD_YEARS, years.max() + X_PAD_YEARS)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    return chart


def form_chart(
    form: pd.DataFrame,
    standings: pd.DataFrame,
    team_colors: Mapping[str, str],
    preset: ChartPreset = ChartPreset.X,
) -> Chart:
    leaders = standings.sort_values("position").head(FORM_TOP)["driver"]
    top = form[form["driver"].isin(set(leaders))].sort_values("avg_finish")
    best = top.iloc[0]
    chart = Chart(
        title=f"{best['name']} chega em melhor forma",
        subtitle=f"Média de chegada nas últimas {int(best['races'])} corridas · "
        f"{FORM_TOP} primeiros do campeonato",
        preset=preset,
    )
    ax = chart.ax
    halo = _halo(chart)
    for row, entry in enumerate(top.to_dict("records")):
        average = float(entry["avg_finish"])
        ax.barh(
            row,
            average,
            height=BAR_HEIGHT,
            color=team_colors.get(str(entry["driver"]), chart.theme.muted),
        )
        ax.text(
            average + LABEL_GAP,
            row,
            f"{entry['driver']} · {format_decimal(average, 1)}",
            va="center",
            color=chart.theme.text_primary,
            fontsize=LABEL_PT,
            path_effects=halo,
        )
    ax.set_ylim(len(top) - 0.5, -0.5)
    ax.set_yticks([])
    ax.set_xlim(0, float(top["avg_finish"].max()) * 1.25 + 1)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=chart.theme.grid, linewidth=0.8)
    ax.set_xlabel("Posição média de chegada (menor é melhor)")
    return chart


def _winners_title(poles: int, total: int, location: str) -> str:
    if total == 1:
        return f"Só uma edição em {location} até aqui"
    if poles == 0:
        return f"A pole não venceu nenhuma das últimas {total} em {location}"
    return f"A pole venceu {poles} das últimas {total} em {location}"


def _halo(chart: Chart) -> list[patheffects.AbstractPathEffect]:
    return [
        patheffects.withStroke(
            linewidth=LABEL_HALO_WIDTH, foreground=chart.theme.surface
        )
    ]
