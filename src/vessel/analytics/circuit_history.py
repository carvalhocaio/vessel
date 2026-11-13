import pandas as pd

from vessel.analytics.form import current_grid
from vessel.analytics.race import BRAZILIAN
from vessel.analytics.registry import (
    CalcInputs,
    Finding,
    Params,
    calculation,
    str_param,
)
from vessel.domain import ParamValue, Source
from vessel.formatting import format_decimal

HISTORY_EDITIONS = 10
FEW_EDITIONS = 5
PIT_LANE_GRID = 0


def editions(history: pd.DataFrame) -> int:
    return int(history["season"].nunique())


def winners(history: pd.DataFrame) -> pd.DataFrame:
    races = history[history["session"] == "race"]
    starters = races.groupby("season")["driver"].count()
    won = races[races["finish"] == 1].copy()
    pit_lane = won["grid"] == PIT_LANE_GRID
    won["from_pit_lane"] = pit_lane
    won["start"] = won["grid"].where(~pit_lane, won["season"].map(starters))
    return won.sort_values("season").reset_index(drop=True)


CIRCUIT_FACTS = (
    "circuit.first_race",
    "circuit.last_winner",
    "circuit.pole_to_win",
    "circuit.furthest_back_winner",
    "circuit.top_current_driver",
    "circuit.team_wins",
    "circuit.best_brazilian",
)


def circuit_params(location: str, editions: int) -> dict[str, ParamValue]:
    return {"location": location, "editions": editions}


@calculation("circuit.first_race", Source.JOLPICA)
def first_race(inputs: CalcInputs, params: Params) -> Finding | None:
    if not inputs.history.empty:
        return None
    location = str_param(params, "location")
    return Finding(
        key="circuit_first_race",
        value=location,
        display=f"Estreia em {location}",
        context=f"Primeira corrida de F1 neste circuito em {location}: "
        "não há histórico de edições anteriores.",
    )


@calculation("circuit.last_winner", Source.JOLPICA)
def last_winner(inputs: CalcInputs, params: Params) -> Finding | None:
    return _last_winner(winners(inputs.history), str_param(params, "location"))


@calculation("circuit.pole_to_win", Source.JOLPICA)
def pole_to_win(inputs: CalcInputs, params: Params) -> Finding | None:
    return _pole_to_win(winners(inputs.history), str_param(params, "location"))


@calculation("circuit.furthest_back_winner", Source.JOLPICA)
def furthest_back_winner(inputs: CalcInputs, params: Params) -> Finding | None:
    return _furthest_back_winner(winners(inputs.history), str_param(params, "location"))


@calculation("circuit.top_current_driver", Source.JOLPICA)
def top_current_driver(inputs: CalcInputs, params: Params) -> Finding | None:
    history = inputs.history
    return _top_current_driver(
        history,
        winners(history),
        current_grid(inputs.season.results),
        str_param(params, "location"),
    )


@calculation("circuit.team_wins", Source.JOLPICA)
def team_wins(inputs: CalcInputs, params: Params) -> Finding | None:
    return _team_wins(winners(inputs.history), str_param(params, "location"))


@calculation("circuit.best_brazilian", Source.JOLPICA)
def best_brazilian(inputs: CalcInputs, params: Params) -> Finding | None:
    return _best_brazilian(inputs.history, str_param(params, "location"))


def _last_winner(won: pd.DataFrame, location: str) -> Finding | None:
    if won.empty:
        return None
    last = won.iloc[-1]
    return Finding(
        key="circuit_last_winner",
        value=str(last["name"]),
        display=f"{last['name']} ({last['season']})",
        context=f"{last['name']} ({last['team']}) venceu a última edição em "
        f"{location}, em {last['season']}, {_start_phrase(last)}.",
    )


def _pole_to_win(won: pd.DataFrame, location: str) -> Finding | None:
    if won.empty:
        return None
    total = len(won)
    poles = int((won["grid"] == 1).sum())
    share = 100 * poles / total
    return Finding(
        key="circuit_pole_to_win",
        value=round(share, 1),
        unit="%",
        display=f"{format_decimal(share, 0)}% ({poles} de {total})",
        context=f"Quem largou na pole venceu {poles} das últimas {total} edições "
        f"em {location}.",
    )


def _furthest_back_winner(won: pd.DataFrame, location: str) -> Finding | None:
    if won.empty:
        return None
    back = won.sort_values(["start", "season"], ascending=[False, False]).iloc[0]
    return Finding(
        key="circuit_furthest_back_winner",
        value=int(back["start"]),
        unit="grid",
        display="pit lane" if back["from_pit_lane"] else f"P{back['start']}",
        context=f"{back['name']} venceu em {location} em {back['season']} "
        f"{_start_phrase(back)}, a vitória de mais longe nas últimas "
        f"{len(won)} edições.",
    )


def _top_current_driver(
    history: pd.DataFrame,
    won: pd.DataFrame,
    current_grid: set[str],
    location: str,
) -> Finding | None:
    races = history[
        (history["session"] == "race") & history["driver"].isin(current_grid)
    ]
    if races.empty:
        return None
    wins = won[won["driver"].isin(current_grid)].groupby("name").size()
    if not wins.empty:
        name, count = str(wins.idxmax()), int(wins.max())
        top = wins[wins == count].index.tolist()
        noun = "vitória" if count == 1 else "vitórias"
        tied = (
            f" (empatado com {', '.join(t for t in top if t != name)})"
            if len(top) > 1
            else ""
        )
        return Finding(
            key="circuit_top_current_driver",
            value=count,
            unit="wins",
            display=f"{count} {noun}",
            context=f"{name} é o piloto do grid atual com mais vitórias em "
            f"{location} nas últimas {editions(history)} edições{tied}.",
        )
    best = races.dropna(subset=["finish"]).sort_values(["finish", "season"]).iloc[0]
    return Finding(
        key="circuit_top_current_driver",
        value=int(best["finish"]),
        unit="position",
        display=f"P{best['finish']}",
        context=f"Nenhum piloto do grid atual venceu em {location}; o melhor "
        f"resultado é P{best['finish']} de {best['name']} em {best['season']}.",
    )


def _team_wins(won: pd.DataFrame, location: str) -> Finding | None:
    if won.empty:
        return None
    counts = won.groupby("team").size().sort_values(ascending=False)
    team, count = str(counts.index[0]), int(counts.iloc[0])
    return Finding(
        key="circuit_team_wins",
        value=count,
        unit="wins",
        display=f"{team}: {count} de {len(won)}",
        context=f"{team} venceu {count} das últimas {len(won)} edições em {location}.",
    )


def _best_brazilian(history: pd.DataFrame, location: str) -> Finding | None:
    races = history[
        (history["session"] == "race") & (history["nationality"] == BRAZILIAN)
    ].dropna(subset=["finish"])
    if races.empty:
        return None
    best = races.sort_values(["finish", "season"], ascending=[True, False]).iloc[0]
    return Finding(
        key="circuit_best_brazilian",
        value=int(best["finish"]),
        unit="position",
        display=f"P{best['finish']} ({best['name']}, {best['season']})",
        context=f"Melhor resultado de um brasileiro em {location} nas últimas "
        f"{editions(history)} edições: {best['name']} ({best['team']}), "
        f"P{best['finish']} em {best['season']}.",
    )


def _start_phrase(row: pd.Series) -> str:
    if bool(row["from_pit_lane"]):
        return "largando do pit lane"
    if int(row["grid"]) == 1:
        return "largando da pole"
    return f"largando de P{row['grid']}"
