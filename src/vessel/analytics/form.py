from dataclasses import dataclass

import pandas as pd

from vessel.domain import Event, EventFormat, EventStatus, Fact, Source
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


def points_at_stake(event: Event) -> int:
    sprint = SPRINT_WIN_POINTS if event.format is EventFormat.SPRINT else 0
    return RACE_WIN_POINTS + sprint


def championship_math(
    standings: pd.DataFrame, events: tuple[Event, ...], event: Event
) -> ChampionshipMath | None:
    if len(standings) < MIN_STANDINGS:
        return None
    ordered = standings.sort_values("position")
    leader, runner_up = ordered.iloc[0], ordered.iloc[1]
    remaining = [e for e in events if e.round >= event.round and not e.is_cancelled]
    available = sum(points_at_stake(e) for e in remaining)
    here = points_at_stake(event)
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
        rounds=tuple(e.round for e in remaining),
        at_risk=tuple(e.round for e in remaining if e.status is EventStatus.AT_RISK),
        verdict=verdict,
    )


def form_facts(form: pd.DataFrame, source: Source) -> tuple[Fact, ...]:
    if form.empty:
        return ()
    facts: list[Fact] = []
    complete = form[form["races"] == form["races"].max()]
    best = complete.iloc[0]
    facts.append(
        Fact(
            key="form_best_average",
            value=round(float(best["avg_finish"]), 1),
            unit="position",
            display=f"média {format_decimal(best['avg_finish'], 1)}",
            context=f"{best['name']} ({best['team']}) tem a melhor média de chegada "
            f"nas últimas {best['races']} corridas: "
            f"{format_decimal(best['avg_finish'], 1)}, com {best['podiums']} pódios "
            f"e {format_decimal(best['points'], 0)} pontos.",
            source=source,
        )
    )
    for key, column, noun in (
        ("form_podium_streak", "podium_streak", "pódios seguidos"),
        ("form_points_streak", "points_streak", "corridas seguidas nos pontos"),
    ):
        top = form.sort_values([column, "avg_finish"], ascending=[False, True]).iloc[0]
        if int(top[column]) >= MIN_STREAK:
            facts.append(
                Fact(
                    key=key,
                    value=int(top[column]),
                    unit="races",
                    display=f"{top[column]} {noun}",
                    context=f"{top['name']} ({top['team']}) chega com {top[column]} "
                    f"{noun}, a maior sequência atual do grid.",
                    source=source,
                )
            )
    worst = form.sort_values(["dnfs", "avg_finish"], ascending=[False, False]).iloc[0]
    if int(worst["dnfs"]) >= MIN_STREAK:
        facts.append(
            Fact(
                key="form_most_dnfs",
                value=int(worst["dnfs"]),
                unit="races",
                display=f"{worst['dnfs']} abandonos",
                context=f"{worst['name']} ({worst['team']}) não terminou "
                f"{worst['dnfs']} das últimas {worst['races']} corridas.",
                source=source,
            )
        )
    return tuple(facts)


def championship_facts(
    math: ChampionshipMath | None, source: Source
) -> tuple[Fact, ...]:
    if math is None:
        return ()
    gap = math.gap
    races = len(math.rounds)
    verdicts = {
        DECIDED: f"{math.leader} já é campeão matematicamente: "
        f"{format_decimal(gap, 0)} pontos de vantagem com {math.available} "
        "ainda em disputa.",
        YES: f"{math.leader} pode ser campeão neste GP: vencendo ({math.at_stake_here} "
        f"pontos) sem {math.runner_up} pontuar, abre "
        f"{format_decimal(gap + math.at_stake_here, 0)} com {math.available_after} "
        "em disputa depois.",
        NO: f"O título não pode ser decidido neste GP: mesmo no melhor cenário, "
        f"{math.leader} abriria {format_decimal(gap + math.at_stake_here, 0)} com "
        f"{math.available_after} ainda em disputa.",
    }
    return (
        Fact(
            key="championship_gap",
            value=gap,
            unit="points",
            display=f"{format_decimal(gap, 0)} pontos",
            context=f"{math.leader} lidera com {format_decimal(math.leader_points, 0)} "
            f"pontos, contra {format_decimal(math.runner_up_points, 0)} de "
            f"{math.runner_up}.",
            source=source,
        ),
        Fact(
            key="championship_points_available",
            value=math.available,
            unit="points",
            display=f"{math.available} pontos",
            context=f"Ainda há {math.available} pontos em disputa em {races} "
            f"{'GP' if races == 1 else 'GPs'} (rodadas "
            f"{', '.join(str(r) for r in math.rounds)}), contando este.",
            source=source,
        ),
        Fact(
            key="championship_can_be_decided",
            value=math.verdict,
            display=math.verdict,
            context=verdicts[math.verdict],
            source=source,
        ),
    )
