from dataclasses import dataclass

import pandas as pd

from vessel.analytics.registry import (
    CalcInputs,
    Finding,
    Params,
    calculation,
    int_list_param,
    int_param,
)
from vessel.domain import Event, EventFormat, EventStatus, ParamValue, Source
from vessel.formatting import format_decimal

FORM_RACES = 5
MIN_STREAK = 2
MIN_STANDINGS = 2
RACE_WIN_POINTS = 25
SPRINT_WIN_POINTS = 8
PODIUM = 3
DECIDED = "já decidido"
YES = "sim"
NO = "não"

FORM_FACTS = (
    "form.best_average",
    "form.podium_streak",
    "form.points_streak",
    "form.most_dnfs",
)
CHAMPIONSHIP_FACTS = (
    "championship.gap",
    "championship.points_available",
    "championship.can_be_decided",
)


@dataclass(frozen=True, slots=True)
class ChampionshipMath:
    leader: str
    leader_points: float
    runner_up: str
    runner_up_points: float
    available: int
    available_after: int
    at_stake_here: int
    rounds: tuple[int, ...]
    at_risk: tuple[int, ...]
    verdict: str

    @property
    def gap(self) -> float:
        return self.leader_points - self.runner_up_points


def current_grid(results: pd.DataFrame) -> set[str]:
    races = results[results["session"] == "race"]
    if races.empty:
        return set()
    last = races["round"].max()
    return {str(driver) for driver in races.loc[races["round"] == last, "driver"]}


def recent_form(results: pd.DataFrame, last: int = FORM_RACES) -> pd.DataFrame:
    races = results[results["session"] == "race"].sort_values("round")
    grid = current_grid(results)
    rows = []
    for driver, starts in races[races["driver"].isin(grid)].groupby("driver"):
        window = starts.tail(last)
        classified = window["position_text"].str.isdigit()
        rows.append(
            {
                "driver": str(driver),
                "name": str(window["name"].iloc[-1]),
                "team": str(window["team"].iloc[-1]),
                "races": len(window),
                "avg_finish": float(window["finish"].mean()),
                "points": float(window["points"].sum()),
                "podiums": int((window["finish"] <= PODIUM).sum()),
                "dnfs": int((~classified).sum()),
                "podium_streak": _streak(starts["finish"] <= PODIUM),
                "points_streak": _streak(starts["points"] > 0),
            }
        )
    form = pd.DataFrame(rows)
    if form.empty:
        return form
    return form.sort_values(["avg_finish", "driver"]).reset_index(drop=True)


def _streak(hits: pd.Series) -> int:
    count = 0
    for hit in reversed(hits.fillna(value=False).astype(bool).tolist()):
        if not hit:
            break
        count += 1
    return count


def form_params(last: int = FORM_RACES) -> dict[str, ParamValue]:
    return {"last": last}


def form_from(inputs: CalcInputs, params: Params) -> pd.DataFrame:
    return recent_form(inputs.season.results, int_param(params, "last"))


@calculation("form.best_average", Source.JOLPICA)
def best_average(inputs: CalcInputs, params: Params) -> Finding | None:
    form = form_from(inputs, params)
    if form.empty:
        return None
    complete = form[form["races"] == form["races"].max()]
    best = complete.iloc[0]
    return Finding(
        key="form_best_average",
        value=round(float(best["avg_finish"]), 1),
        unit="position",
        display=f"média {format_decimal(best['avg_finish'], 1)}",
        context=f"{best['name']} ({best['team']}) tem a melhor média de chegada "
        f"nas últimas {best['races']} corridas: "
        f"{format_decimal(best['avg_finish'], 1)}, com {best['podiums']} pódios "
        f"e {format_decimal(best['points'], 0)} pontos.",
    )


@calculation("form.podium_streak", Source.JOLPICA)
def podium_streak(inputs: CalcInputs, params: Params) -> Finding | None:
    return _streak_finding(
        form_from(inputs, params),
        "form_podium_streak",
        "podium_streak",
        "pódios seguidos",
    )


@calculation("form.points_streak", Source.JOLPICA)
def points_streak(inputs: CalcInputs, params: Params) -> Finding | None:
    return _streak_finding(
        form_from(inputs, params),
        "form_points_streak",
        "points_streak",
        "corridas seguidas nos pontos",
    )


@calculation("form.most_dnfs", Source.JOLPICA)
def most_dnfs(inputs: CalcInputs, params: Params) -> Finding | None:
    form = form_from(inputs, params)
    if form.empty:
        return None
    worst = form.sort_values(["dnfs", "avg_finish"], ascending=[False, False]).iloc[0]
    if int(worst["dnfs"]) < MIN_STREAK:
        return None
    return Finding(
        key="form_most_dnfs",
        value=int(worst["dnfs"]),
        unit="races",
        display=f"{worst['dnfs']} abandonos",
        context=f"{worst['name']} ({worst['team']}) não terminou "
        f"{worst['dnfs']} das últimas {worst['races']} corridas.",
    )


def _streak_finding(
    form: pd.DataFrame, key: str, column: str, noun: str
) -> Finding | None:
    if form.empty:
        return None
    top = form.sort_values([column, "avg_finish"], ascending=[False, True]).iloc[0]
    if int(top[column]) < MIN_STREAK:
        return None
    return Finding(
        key=key,
        value=int(top[column]),
        unit="races",
        display=f"{top[column]} {noun}",
        context=f"{top['name']} ({top['team']}) chega com {top[column]} "
        f"{noun}, a maior sequência atual do grid.",
    )


def championship_params(
    events: tuple[Event, ...], event: Event
) -> dict[str, ParamValue]:
    remaining = [e for e in events if e.round >= event.round and not e.is_cancelled]
    return {
        "round": event.round,
        "rounds": [e.round for e in remaining],
        "sprint_rounds": [e.round for e in remaining if e.format is EventFormat.SPRINT],
        "at_risk_rounds": [
            e.round for e in remaining if e.status is EventStatus.AT_RISK
        ],
    }


def championship_math(
    standings: pd.DataFrame, params: Params
) -> ChampionshipMath | None:
    if len(standings) < MIN_STANDINGS:
        return None
    this_round = int_param(params, "round")
    rounds = int_list_param(params, "rounds")
    sprints = set(int_list_param(params, "sprint_rounds"))

    def stake(round_: int) -> int:
        return RACE_WIN_POINTS + (SPRINT_WIN_POINTS if round_ in sprints else 0)

    ordered = standings.sort_values("position")
    leader, runner_up = ordered.iloc[0], ordered.iloc[1]
    available = sum(stake(round_) for round_ in rounds)
    here = stake(this_round)
    after = available - here
    gap = float(leader["points"]) - float(runner_up["points"])
    if gap > available:
        verdict = DECIDED
    elif gap + here > after:
        verdict = YES
    else:
        verdict = NO
    return ChampionshipMath(
        leader=str(leader["name"]),
        leader_points=float(leader["points"]),
        runner_up=str(runner_up["name"]),
        runner_up_points=float(runner_up["points"]),
        available=available,
        available_after=after,
        at_stake_here=here,
        rounds=tuple(rounds),
        at_risk=tuple(int_list_param(params, "at_risk_rounds")),
        verdict=verdict,
    )


@calculation("championship.gap", Source.JOLPICA)
def championship_gap(inputs: CalcInputs, params: Params) -> Finding | None:
    math = championship_math(inputs.season.standings, params)
    if math is None:
        return None
    return Finding(
        key="championship_gap",
        value=math.gap,
        unit="points",
        display=f"{format_decimal(math.gap, 0)} pontos",
        context=f"{math.leader} lidera com {format_decimal(math.leader_points, 0)} "
        f"pontos, contra {format_decimal(math.runner_up_points, 0)} de "
        f"{math.runner_up}.",
    )


@calculation("championship.points_available", Source.JOLPICA)
def championship_points_available(inputs: CalcInputs, params: Params) -> Finding | None:
    math = championship_math(inputs.season.standings, params)
    if math is None:
        return None
    races = len(math.rounds)
    return Finding(
        key="championship_points_available",
        value=math.available,
        unit="points",
        display=f"{math.available} pontos",
        context=f"Ainda há {math.available} pontos em disputa em {races} "
        f"{'GP' if races == 1 else 'GPs'} (rodadas "
        f"{', '.join(str(r) for r in math.rounds)}), contando este.",
    )


@calculation("championship.can_be_decided", Source.JOLPICA)
def championship_can_be_decided(inputs: CalcInputs, params: Params) -> Finding | None:
    math = championship_math(inputs.season.standings, params)
    if math is None:
        return None
    best_lead = format_decimal(math.gap + math.at_stake_here, 0)
    verdicts = {
        DECIDED: f"{math.leader} já é campeão matematicamente: "
        f"{format_decimal(math.gap, 0)} pontos de vantagem com {math.available} "
        "ainda em disputa.",
        YES: f"{math.leader} pode ser campeão neste GP: vencendo ({math.at_stake_here} "
        f"pontos) sem {math.runner_up} pontuar, abre {best_lead} com "
        f"{math.available_after} em disputa depois.",
        NO: "O título não pode ser decidido neste GP: mesmo no melhor cenário, "
        f"{math.leader} abriria {best_lead} com {math.available_after} ainda em "
        "disputa.",
    }
    return Finding(
        key="championship_can_be_decided",
        value=math.verdict,
        display=math.verdict,
        context=verdicts[math.verdict],
    )
