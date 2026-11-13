from collections.abc import Mapping

import pandas as pd

from vessel.analytics.circuit_history import winners
from vessel.analytics.form import form_from
from vessel.analytics.registry import CalcInputs, Params, chart_calculation, str_param
from vessel.charts.specs.race import team_colors
from vessel.domain import (
    Axis,
    AxisFormat,
    GridTimelineSpec,
    RankedDotsSpec,
    RankedPoint,
    RankedSeries,
    Source,
    TimelinePoint,
    TimelineSeries,
)
from vessel.formatting import format_decimal

HISTORY_SOURCES = (Source.JOLPICA,)
FORM_SOURCES = (Source.FASTF1, Source.JOLPICA)
FORM_TOP = 10


def grid_timeline_spec(history: pd.DataFrame, location: str) -> GridTimelineSpec:
    won = winners(history)
    total, poles = len(won), int((won["grid"] == 1).sum())
    points = tuple(
        TimelinePoint(
            season=int(row["season"]),
            start=int(row["start"]),
            from_pit_lane=bool(row["from_pit_lane"]),
            driver=str(row["name"]),
            label=str(row["driver"]),
            start_label="pit lane" if row["from_pit_lane"] else f"P{row['start']}",
        )
        for row in won.to_dict("records")
    )
    return GridTimelineSpec(
        title=_winners_title(poles, total, location),
        subtitle=f"Posição de largada do vencedor em cada edição · {location}",
        sources=HISTORY_SOURCES,
        x=Axis(
            label="Temporada",
            format=AxisFormat.INTEGER,
            domain=(points[0].season, points[-1].season),
        ),
        y=Axis(
            label="Largada",
            format=AxisFormat.POSITION,
            inverted=True,
            domain=(1, max(point.start for point in points)),
        ),
        series=(TimelineSeries(id="winners", label="Vencedores", points=points),),
    )


def ranked_dots_spec(
    form: pd.DataFrame, standings: pd.DataFrame, team_colors: Mapping[str, str]
) -> RankedDotsSpec:
    leaders = standings.sort_values("position").head(FORM_TOP)["driver"]
    top = form[form["driver"].isin(set(leaders))].sort_values("avg_finish")
    best = top.iloc[0]
    return RankedDotsSpec(
        title=f"{best['name']} chega em melhor forma",
        subtitle=f"Média de chegada nas últimas {int(best['races'])} corridas · "
        f"{FORM_TOP} primeiros do campeonato",
        sources=FORM_SOURCES,
        x=Axis(
            label="Posição média de chegada (menor é melhor)",
            format=AxisFormat.DECIMAL,
            domain=(0, float(top["avg_finish"].max())),
        ),
        y=Axis(format=AxisFormat.POSITION, inverted=True),
        series=tuple(
            RankedSeries(
                id=str(entry["driver"]),
                label=str(entry["name"]),
                color=team_colors.get(str(entry["driver"])),
                point=RankedPoint(
                    value=float(entry["avg_finish"]),
                    value_label=format_decimal(float(entry["avg_finish"]), 1),
                ),
                detail_label=f"{entry['driver']} · "
                f"{format_decimal(float(entry['avg_finish']), 1)}",
            )
            for entry in top.to_dict("records")
        ),
    )


def _winners_title(poles: int, total: int, location: str) -> str:
    if total == 1:
        return f"Só uma edição em {location} até aqui"
    if poles == 0:
        return f"A pole não venceu nenhuma das últimas {total} em {location}"
    return f"A pole venceu {poles} das últimas {total} em {location}"


@chart_calculation("chart.winners")
def winners_chart(inputs: CalcInputs, params: Params) -> GridTimelineSpec:
    return grid_timeline_spec(inputs.history, str_param(params, "location"))


@chart_calculation("chart.form")
def form_chart(inputs: CalcInputs, params: Params) -> RankedDotsSpec:
    race = inputs.race_tables
    colors = team_colors(race.results) if race is not None else {}
    return ranked_dots_spec(form_from(inputs, params), inputs.season.standings, colors)
