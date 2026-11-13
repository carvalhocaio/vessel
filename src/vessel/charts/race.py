import pandas as pd
from matplotlib import patheffects

from vessel.analytics.race import (
    driver_names,
    finishing_order,
    highlighted_drivers,
    pit_stops,
    winner,
)
from vessel.charts.canvas import Chart
from vessel.domain import ChartPreset
from vessel.formatting import compound_name

DRIVER_LABEL_PT = 8
COMPOUND_LABEL_PT = 7
MIN_LAPS_FOR_LETTER = 4
BAR_HEIGHT = 0.72
HIGHLIGHT_WIDTH = 2.4
RECESSIVE_WIDTH = 1.0
RECESSIVE_ALPHA = 0.35
LABEL_GAP_LAPS = 0.8
RIGHT_PAD_LAPS = 4
LABEL_HALO_WIDTH = 3

COMPOUND_CODES = {
    "SOFT": "S",
    "MEDIUM": "M",
    "HARD": "H",
    "INTERMEDIATE": "INT",
    "WET": "W",
}


def stint_chart(
    stints: pd.DataFrame,
    laps: pd.DataFrame,
    results: pd.DataFrame,
    preset: ChartPreset = ChartPreset.X,
) -> Chart:
    order = finishing_order(results, laps)
    leader = winner(results)
    stops = pit_stops(laps, leader)
    noun = "parada" if stops == 1 else "paradas"
    chart = Chart(
        title=f"{driver_names(results)[leader]} venceu com {stops} {noun}",
        subtitle=f"Stints em ordem de chegada · {_compound_legend(stints)} · voltas",
        preset=preset,
    )
    ax = chart.ax
    rows = {driver: index for index, driver in enumerate(order)}
    for stint in stints[stints["driver"].isin(rows)].to_dict("records"):
        row = rows[str(stint["driver"])]
        start, length = int(stint["lap_start"]) - 1, int(stint["laps"])
        ax.barh(
            row,
            width=length,
            left=start,
            height=BAR_HEIGHT,
            color=str(stint["compound_color"]),
            edgecolor=chart.theme.surface,
            linewidth=0.8,
        )
        if length >= MIN_LAPS_FOR_LETTER:
            ax.text(
                start + length / 2,
                row,
                _compound_code(str(stint["compound"])),
                ha="center",
                va="center",
                color=chart.theme.surface,
                fontsize=COMPOUND_LABEL_PT,
                fontweight="bold",
            )
    ax.set_yticks(range(len(order)), labels=order, fontsize=DRIVER_LABEL_PT)
    ax.set_ylim(len(order) - 0.5, -0.5)
    ax.set_xlim(0, int(laps["lap"].max()))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=chart.theme.grid, linewidth=0.8)
    return chart


def position_chart(
    positions: pd.DataFrame,
    laps: pd.DataFrame,
    results: pd.DataFrame,
    preset: ChartPreset = ChartPreset.X,
) -> Chart:
    order = finishing_order(results, laps)
    leader = winner(results)
    chart = Chart(
        title=_position_title(results, leader),
        subtitle="Posição volta a volta · destaque para o pódio e brasileiros",
        preset=preset,
    )
    ax = chart.ax
    colors = {
        str(driver): str(color)
        for driver, color in zip(results["driver"], results["team_color"], strict=True)
        if pd.notna(color)
    }
    highlighted = highlighted_drivers(results)
    dashed = _second_teammates([d for d in order if d in highlighted], colors)
    halo = [
        patheffects.withStroke(
            linewidth=LABEL_HALO_WIDTH, foreground=chart.theme.surface
        )
    ]
    for driver in reversed(order):
        trace = positions[positions["driver"] == driver].sort_values("lap")
        if trace.empty:
            continue
        is_highlight = driver in highlighted
        color = str(colors.get(driver) or chart.theme.muted)
        ax.plot(
            trace["lap"].astype(int),
            trace["position"].astype(int),
            color=color,
            linewidth=HIGHLIGHT_WIDTH if is_highlight else RECESSIVE_WIDTH,
            alpha=1.0 if is_highlight else RECESSIVE_ALPHA,
            linestyle="--" if driver in dashed else "-",
            zorder=3 if is_highlight else 2,
            solid_capstyle="round",
        )
        last = trace.iloc[-1]
        ax.text(
            int(last["lap"]) + LABEL_GAP_LAPS,
            int(last["position"]),
            driver,
            va="center",
            color=chart.theme.text_primary if is_highlight else chart.theme.muted,
            fontsize=DRIVER_LABEL_PT,
            fontweight="bold" if is_highlight else "normal",
            clip_on=False,
            zorder=4,
            path_effects=halo,
        )
    field = len(order)
    ax.set_ylim(field + 0.5, 0.5)
    ax.set_yticks([1, *range(5, field + 1, 5)])
    ax.set_xlim(0, int(laps["lap"].max()) + RIGHT_PAD_LAPS)
    ax.set_xlabel("Volta")
    return chart


def _position_title(results: pd.DataFrame, leader: str) -> str:
    row = results.set_index("driver").loc[leader]
    name = driver_names(results)[leader]
    if pd.isna(row["grid"]):
        return f"{name} largou do pit lane e venceu"
    grid = int(row["grid"])
    if grid == 1:
        return f"{name} largou na pole e venceu"
    return f"{name} largou em P{grid} e venceu"


def _compound_code(compound: str) -> str:
    return COMPOUND_CODES.get(compound, compound[:1])


def _compound_legend(stints: pd.DataFrame) -> str:
    used = [str(compound) for compound in stints["compound"].dropna().unique()]
    known = [compound for compound in COMPOUND_CODES if compound in used]
    return ", ".join(
        f"{COMPOUND_CODES[compound]} {compound_name(compound)}" for compound in known
    )


def _second_teammates(ordered: list[str], colors: dict[str, str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for driver in ordered:
        color = colors.get(driver)
        if color in seen:
            repeated.add(driver)
        elif color:
            seen.add(color)
    return repeated
