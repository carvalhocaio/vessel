import pandas as pd

from vessel.analytics.race import (
    driver_names,
    finishing_order,
    highlighted_drivers,
    pit_stops,
    positions_by_lap,
    stint_summary,
    winner,
)
from vessel.analytics.registry import CalcInputs, Params, chart_calculation
from vessel.domain import (
    Axis,
    AxisFormat,
    LegendEntry,
    PositionLinesSpec,
    PositionPoint,
    PositionSeries,
    Source,
    StintBarsSpec,
    StintSegment,
    StintSeries,
)
from vessel.formatting import compound_name

STINT_SOURCES = (Source.FASTF1,)
POSITION_SOURCES = (Source.FASTF1, Source.JOLPICA)

COMPOUND_CODES = {
    "SOFT": "S",
    "MEDIUM": "M",
    "HARD": "H",
    "INTERMEDIATE": "INT",
    "WET": "W",
}


def stint_bars_spec(
    stints: pd.DataFrame, laps: pd.DataFrame, results: pd.DataFrame
) -> StintBarsSpec:
    order = finishing_order(results, laps)
    names = driver_names(results)
    leader = winner(results)
    stops = pit_stops(laps, leader)
    noun = "parada" if stops == 1 else "paradas"
    legend = _legend(stints)
    legend_text = ", ".join(f"{entry.code} {entry.label}" for entry in legend)
    return StintBarsSpec(
        title=f"{names[leader]} venceu com {stops} {noun}",
        subtitle=f"Stints em ordem de chegada · {legend_text} · voltas",
        sources=STINT_SOURCES,
        x=Axis(
            label="Volta",
            unit="lap",
            format=AxisFormat.INTEGER,
            domain=(0, int(laps["lap"].max())),
        ),
        y=Axis(format=AxisFormat.POSITION, inverted=True),
        series=tuple(
            StintSeries(
                id=driver,
                label=driver,
                segments=_segments(stints[stints["driver"] == driver]),
            )
            for driver in order
        ),
        legend=legend,
    )


def position_lines_spec(
    positions: pd.DataFrame, laps: pd.DataFrame, results: pd.DataFrame
) -> PositionLinesSpec:
    order = finishing_order(results, laps)
    colors = team_colors(results)
    highlighted = highlighted_drivers(results)
    dashed = second_teammates([d for d in order if d in highlighted], colors)
    series = []
    for driver in order:
        trace = positions[positions["driver"] == driver].sort_values("lap")
        if trace.empty:
            continue
        series.append(
            PositionSeries(
                id=driver,
                label=driver,
                color=colors.get(driver),
                highlighted=driver in highlighted,
                points=tuple(
                    PositionPoint(lap=int(lap), position=int(position))
                    for lap, position in zip(
                        trace["lap"], trace["position"], strict=True
                    )
                ),
                end_label=driver,
                dashed=driver in dashed,
            )
        )
    return PositionLinesSpec(
        title=_position_title(results, winner(results)),
        subtitle="Posição volta a volta · destaque para o pódio e brasileiros",
        sources=POSITION_SOURCES,
        x=Axis(
            label="Volta",
            unit="lap",
            format=AxisFormat.INTEGER,
            domain=(0, int(laps["lap"].max())),
        ),
        y=Axis(
            label="Posição",
            format=AxisFormat.POSITION,
            inverted=True,
            domain=(1, len(order)),
        ),
        series=tuple(series),
    )


def team_colors(results: pd.DataFrame) -> dict[str, str]:
    return {
        str(driver): str(color)
        for driver, color in zip(results["driver"], results["team_color"], strict=True)
        if pd.notna(color)
    }


def second_teammates(ordered: list[str], colors: dict[str, str]) -> set[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for driver in ordered:
        color = colors.get(driver)
        if color in seen:
            repeated.add(driver)
        elif color:
            seen.add(color)
    return repeated


def compound_code(compound: str) -> str:
    return COMPOUND_CODES.get(compound, compound[:1])


def _segments(stints: pd.DataFrame) -> tuple[StintSegment, ...]:
    return tuple(
        StintSegment(
            start_lap=int(stint["lap_start"]),
            end_lap=int(stint["lap_end"]),
            laps=int(stint["laps"]),
            category=str(stint["compound"]),
            category_label=compound_code(str(stint["compound"])),
            color=str(stint["compound_color"]),
        )
        for stint in stints.sort_values("stint").to_dict("records")
    )


def _legend(stints: pd.DataFrame) -> tuple[LegendEntry, ...]:
    used = stints.dropna(subset=["compound"]).drop_duplicates("compound")
    colors = dict(zip(used["compound"], used["compound_color"], strict=True))
    return tuple(
        LegendEntry(
            code=code,
            label=compound_name(compound),
            color=str(colors[compound]),
        )
        for compound, code in COMPOUND_CODES.items()
        if compound in colors
    )


def _position_title(results: pd.DataFrame, leader: str) -> str:
    row = results.set_index("driver").loc[leader]
    name = driver_names(results)[leader]
    if pd.isna(row["grid"]):
        return f"{name} largou do pit lane e venceu"
    grid = int(row["grid"])
    if grid == 1:
        return f"{name} largou na pole e venceu"
    return f"{name} largou em P{grid} e venceu"


@chart_calculation("chart.stints")
def stints_chart(inputs: CalcInputs, params: Params) -> StintBarsSpec:
    laps, results = inputs.race.laps, inputs.race.results
    return stint_bars_spec(stint_summary(laps), laps, results)


@chart_calculation("chart.positions")
def positions_chart(inputs: CalcInputs, params: Params) -> PositionLinesSpec:
    laps, results = inputs.race.laps, inputs.race.results
    return position_lines_spec(positions_by_lap(laps, results), laps, results)
