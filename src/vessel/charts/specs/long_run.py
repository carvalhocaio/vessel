import pandas as pd

from vessel.analytics.long_run import MIN_LONG_RUN_LAPS, team_ranking
from vessel.domain import (
    Axis,
    AxisFormat,
    RangedDotsSpec,
    RangedPoint,
    RangedSeries,
    SessionKind,
    Source,
)
from vessel.formatting import (
    compound_name,
    format_lap_time,
    session_label,
    session_phrase,
)

SOURCES = (Source.FASTF1,)


def ranged_dots_spec(runs: pd.DataFrame, kind: SessionKind) -> RangedDotsSpec:
    leader = team_ranking(runs).iloc[0]
    return RangedDotsSpec(
        title=f"{leader['team']} tem o melhor ritmo {session_phrase(kind)}",
        subtitle=f"{session_label(kind)} · mediana e intervalo interquartil por "
        f"piloto · voltas limpas, mínimo de {MIN_LONG_RUN_LAPS}",
        sources=SOURCES,
        x=Axis(
            label="Tempo de volta",
            unit="s",
            format=AxisFormat.LAP_TIME,
            domain=(float(runs["q1_s"].min()), float(runs["q3_s"].max())),
        ),
        y=Axis(format=AxisFormat.POSITION, inverted=True),
        series=tuple(_series(run) for run in runs.to_dict("records")),
    )


def _series(run: dict[object, object]) -> RangedSeries:
    median, low, high = (float(str(run[key])) for key in ("median_s", "q1_s", "q3_s"))
    color = run["team_color"]
    return RangedSeries(
        id=str(run["driver"]),
        label=str(run["driver"]),
        color=str(color) if isinstance(color, str) and color else None,
        point=RangedPoint(
            value=median,
            low=low,
            high=high,
            value_label=format_lap_time(median),
            range_label=f"{format_lap_time(low)} a {format_lap_time(high)}",
        ),
        detail_label=f"{run['driver']} · {compound_name(str(run['compound']))} · "
        f"{run['laps']} voltas",
    )
