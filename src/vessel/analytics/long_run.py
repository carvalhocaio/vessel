from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd

from vessel.analytics.race import BRAZILIAN, clean_laps
from vessel.analytics.registry import (
    CalcInputs,
    Finding,
    Params,
    calculation,
    float_param,
    int_param,
)
from vessel.domain import ParamValue, Source
from vessel.formatting import (
    compound_name,
    format_decimal,
    format_lap_time,
    format_signed,
)

MIN_LONG_RUN_LAPS = 6
OUTLIER_RATIO = 1.07
SMALL_SAMPLE_LAPS = 8
FIRST_QUARTILE = 0.25
THIRD_QUARTILE = 0.75
MIN_COMPARED = 2

RUN_COLUMNS = [
    "rank",
    "driver",
    "name",
    "team",
    "team_color",
    "nationality",
    "compound",
    "laps",
    "tyre_life_start",
    "mean_s",
    "median_s",
    "std_s",
    "q1_s",
    "q3_s",
    "degradation_s",
]


class NoLongRunError(ValueError):
    pass


def long_run_laps(
    laps: pd.DataFrame,
    min_laps: int = MIN_LONG_RUN_LAPS,
    outlier_ratio: float = OUTLIER_RATIO,
) -> pd.DataFrame:
    clean = clean_laps(laps).dropna(subset=["stint"]).sort_values(["driver", "lap"])
    candidates = [
        run
        for _, stint in clean.groupby(["driver", "stint"])
        for run in _stint_runs(stint, min_laps, outlier_ratio)
    ]
    if not candidates:
        return clean.iloc[0:0]
    best = sorted(
        candidates,
        key=lambda run: (len(run), -float(run["lap_time_s"].median())),
        reverse=True,
    )
    chosen: dict[str, pd.DataFrame] = {}
    for run in best:
        chosen.setdefault(str(run["driver"].iloc[0]), run)
    return pd.concat(chosen.values(), ignore_index=True)


def _stint_runs(
    stint: pd.DataFrame, min_laps: int, outlier_ratio: float
) -> list[pd.DataFrame]:
    ceiling = float(stint["lap_time_s"].median()) * outlier_ratio
    sequence = stint["lap"].astype("int64").diff().ne(1).cumsum()
    runs = []
    for _, run in stint.groupby(sequence):
        kept = run[run["lap_time_s"] <= ceiling]
        if len(kept) >= min_laps:
            runs.append(kept)
    return runs


def degradation(run: pd.DataFrame) -> float | None:
    tyre_life = run["tyre_life"].astype("Float64")
    if tyre_life.isna().any() or tyre_life.nunique() < MIN_COMPARED:
        return None
    times = run["lap_time_s"].astype("Float64")
    return float(times.cov(tyre_life) / tyre_life.var())


def long_runs(
    laps: pd.DataFrame,
    drivers: pd.DataFrame,
    min_laps: int = MIN_LONG_RUN_LAPS,
    outlier_ratio: float = OUTLIER_RATIO,
) -> pd.DataFrame:
    selected = long_run_laps(laps, min_laps, outlier_ratio)
    profiles = {str(row["driver"]): row for row in drivers.to_dict("records")}
    rows = []
    for driver, run in selected.groupby("driver"):
        times = run["lap_time_s"].astype(float)
        profile = profiles.get(str(driver))
        rows.append(
            {
                "driver": str(driver),
                "name": _field(profile, "name", str(driver)),
                "team": _field(profile, "team", str(run["team"].iloc[0])),
                "team_color": _field(profile, "team_color", None),
                "nationality": _field(profile, "nationality", None),
                "compound": str(run["compound"].iloc[0]),
                "laps": len(run),
                "tyre_life_start": _optional_int(run["tyre_life"].iloc[0]),
                "mean_s": times.mean(),
                "median_s": times.median(),
                "std_s": times.std(),
                "q1_s": times.quantile(FIRST_QUARTILE),
                "q3_s": times.quantile(THIRD_QUARTILE),
                "degradation_s": degradation(run),
            }
        )
    if not rows:
        return pd.DataFrame(columns=RUN_COLUMNS)
    runs = pd.DataFrame(rows).sort_values(["median_s", "driver"]).reset_index(drop=True)
    runs.insert(0, "rank", range(1, len(runs) + 1))
    return runs[RUN_COLUMNS]


def team_ranking(runs: pd.DataFrame) -> pd.DataFrame:
    best = runs.sort_values("median_s").drop_duplicates("team").reset_index(drop=True)
    return best.assign(team_rank=range(1, len(best) + 1))


LONG_RUN_FACTS = (
    "long_run.pace_gap_top_teams",
    "long_run.highest_degradation",
    "long_run.lowest_degradation",
    "long_run.longest_run",
    "long_run.best_brazilian_rank",
)


def long_run_params() -> dict[str, ParamValue]:
    return {"min_laps": MIN_LONG_RUN_LAPS, "outlier_ratio": OUTLIER_RATIO}


def runs_from(inputs: CalcInputs, params: Params) -> pd.DataFrame:
    return long_runs(
        inputs.session.laps,
        inputs.session.drivers,
        min_laps=int_param(params, "min_laps"),
        outlier_ratio=float_param(params, "outlier_ratio"),
    )


@calculation("long_run.pace_gap_top_teams", Source.FASTF1)
def top_teams_comparison(inputs: CalcInputs, params: Params) -> Finding | None:
    runs = runs_from(inputs, params)
    if runs.empty:
        return None
    ranking = team_ranking(runs)
    if len(ranking) < MIN_COMPARED:
        return None
    leader, runner_up = ranking.iloc[0], ranking.iloc[1]
    compound = str(leader["compound"])
    rivals = runs[(runs["compound"] == compound) & (runs["team"] != leader["team"])]
    if rivals.empty:
        pair = (
            f"{compound_name(compound)} vs {compound_name(str(runner_up['compound']))}"
        )
        return Finding(
            key="top_teams_compound_mismatch",
            value=pair,
            display=pair,
            context=f"{_run_phrase(leader)} e {_run_phrase(runner_up)} usaram "
            "compostos diferentes; nenhuma outra equipe fez long run com o pneu "
            f"{compound_name(compound)}, então não há comparação direta de ritmo.",
        )
    rival = rivals.sort_values("median_s").iloc[0]
    gap = float(rival["median_s"]) - float(leader["median_s"])
    context = (
        f"No pneu {compound_name(compound)}, {_run_phrase(leader)} teve mediana "
        f"{format_lap_time(float(leader['median_s']))} contra "
        f"{format_lap_time(float(rival['median_s']))} de {_run_phrase(rival)}."
    )
    if runner_up["team"] != rival["team"]:
        context += (
            f" {runner_up['team']} foi a 2ª no ranking geral, mas com pneu "
            f"{compound_name(str(runner_up['compound']))}, sem comparação direta."
        )
    return Finding(
        key="top_teams_pace_gap",
        value=round(gap, 3),
        unit="s/lap",
        display=f"{format_decimal(gap, 3)} s/volta",
        context=context,
    )


@calculation("long_run.highest_degradation", Source.FASTF1)
def highest_degradation(inputs: CalcInputs, params: Params) -> Finding | None:
    runs = runs_from(inputs, params)
    if runs.empty:
        return None
    rated = runs.dropna(subset=["degradation_s"])
    if rated.empty:
        return None
    return _degradation_fact(
        "highest_degradation", rated.sort_values("degradation_s").iloc[-1]
    )


@calculation("long_run.lowest_degradation", Source.FASTF1)
def lowest_degradation(inputs: CalcInputs, params: Params) -> Finding | None:
    runs = runs_from(inputs, params)
    if runs.empty:
        return None
    rated = runs.dropna(subset=["degradation_s"])
    if len(rated) < MIN_COMPARED:
        return None
    return _degradation_fact(
        "lowest_degradation", rated.sort_values("degradation_s").iloc[0]
    )


@calculation("long_run.longest_run", Source.FASTF1)
def longest_long_run(inputs: CalcInputs, params: Params) -> Finding | None:
    runs = runs_from(inputs, params)
    if runs.empty:
        return None
    run = runs.sort_values(["laps", "median_s"], ascending=[False, True]).iloc[0]
    return Finding(
        key="longest_long_run",
        value=int(run["laps"]),
        unit="laps",
        display=f"{int(run['laps'])} voltas",
        context=f"{run['name']} ({run['team']}) fez o long run mais longo: "
        f"{int(run['laps'])} voltas limpas de pneu "
        f"{compound_name(str(run['compound']))}, mediana "
        f"{format_lap_time(float(run['median_s']))}.",
    )


@calculation("long_run.best_brazilian_rank", Source.FASTF1)
def best_brazilian_rank(inputs: CalcInputs, params: Params) -> Finding | None:
    runs = runs_from(inputs, params)
    if runs.empty:
        return None
    brazilians = runs[runs["nationality"] == BRAZILIAN]
    if brazilians.empty:
        return None
    run = brazilians.sort_values("rank").iloc[0]
    rank, total = int(run["rank"]), len(runs)
    return Finding(
        key="best_brazilian_rank",
        value=rank,
        unit="position",
        display=f"{rank}º de {total}",
        context=f"{run['name']} ({run['team']}) foi o {rank}º entre {total} pilotos "
        f"no ranking de long run por mediana, com {_run_detail(run)}.",
    )


def _degradation_fact(key: str, run: pd.Series) -> Finding:
    value = float(run["degradation_s"])
    return Finding(
        key=key,
        value=round(value, 3),
        unit="s/lap",
        display=f"{format_signed(value, 3)} s/volta",
        context=f"{run['name']} ({run['team']}): tempo de volta variou "
        f"{format_signed(value, 3)} s por volta de vida do pneu, com "
        f"{_run_detail(run)}.",
    )


def _run_phrase(run: pd.Series) -> str:
    return f"{run['team']} ({run['name']}, {_run_detail(run)})"


def _run_detail(run: pd.Series) -> str:
    return f"pneu {compound_name(str(run['compound']))} em {int(run['laps'])} voltas"


def _field(
    profile: Mapping[Hashable, Any] | None, column: str, default: str | None
) -> str | None:
    if profile is None or pd.isna(profile[column]):
        return default
    return str(profile[column])


def _optional_int(value: Any) -> int | None:
    return None if pd.isna(value) else int(value)
