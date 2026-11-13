import pandas as pd

from vessel.analytics.race import BRAZILIAN
from vessel.domain import Fact, Source
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


def circuit_facts(
    history: pd.DataFrame,
    current_grid: set[str],
    location: str,
    source: Source,
) -> tuple[Fact, ...]:
    if history.empty:
        return (
            Fact(
                key="circuit_first_race",
                value=location,
                display=f"Estreia em {location}",
                context=f"Primeira corrida de F1 neste circuito em {location}: "
                "não há histórico de edições anteriores.",
                source=source,
            ),
        )
    won = winners(history)
    facts = (
        _last_winner(won, location, source),
        _pole_to_win(won, location, source),
        _furthest_back_winner(won, location, source),
        _top_current_driver(history, won, current_grid, location, source),
        _team_wins(won, location, source),
        _best_brazilian(history, location, source),
    )
    return tuple(fact for fact in facts if fact is not None)


def _last_winner(won: pd.DataFrame, location: str, source: Source) -> Fact | None:
    if won.empty:
        return None
    last = won.iloc[-1]
    return Fact(
        key="circuit_last_winner",
        value=str(last["name"]),
        display=f"{last['name']} ({last['season']})",
        context=f"{last['name']} ({last['team']}) venceu a última edição em "
        f"{location}, em {last['season']}, {_start_phrase(last)}.",
        source=source,
    )


def _pole_to_win(won: pd.DataFrame, location: str, source: Source) -> Fact | None:
    if won.empty:
        return None
    total = len(won)
    poles = int((won["grid"] == 1).sum())
    share = 100 * poles / total
    return Fact(
        key="circuit_pole_to_win",
        value=round(share, 1),
        unit="%",
        display=f"{format_decimal(share, 0)}% ({poles} de {total})",
        context=f"Quem largou na pole venceu {poles} das últimas {total} edições "
        f"em {location}.",
        source=source,
    )


def _furthest_back_winner(
    won: pd.DataFrame, location: str, source: Source
) -> Fact | None:
    if won.empty:
        return None
    back = won.sort_values(["start", "season"], ascending=[False, False]).iloc[0]
    return Fact(
        key="circuit_furthest_back_winner",
        value=int(back["start"]),
        unit="grid",
        display="pit lane" if back["from_pit_lane"] else f"P{back['start']}",
        context=f"{back['name']} venceu em {location} em {back['season']} "
        f"{_start_phrase(back)}, a vitória de mais longe nas últimas "
        f"{len(won)} edições.",
        source=source,
    )


def _top_current_driver(
    history: pd.DataFrame,
    won: pd.DataFrame,
    current_grid: set[str],
    location: str,
    source: Source,
) -> Fact | None:
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
        return Fact(
            key="circuit_top_current_driver",
            value=count,
            unit="wins",
            display=f"{count} {noun}",
            context=f"{name} é o piloto do grid atual com mais vitórias em "
            f"{location} nas últimas {editions(history)} edições{tied}.",
            source=source,
        )
    best = races.dropna(subset=["finish"]).sort_values(["finish", "season"]).iloc[0]
    return Fact(
        key="circuit_top_current_driver",
        value=int(best["finish"]),
        unit="position",
        display=f"P{best['finish']}",
        context=f"Nenhum piloto do grid atual venceu em {location}; o melhor "
        f"resultado é P{best['finish']} de {best['name']} em {best['season']}.",
        source=source,
    )


def _team_wins(won: pd.DataFrame, location: str, source: Source) -> Fact | None:
    if won.empty:
        return None
    counts = won.groupby("team").size().sort_values(ascending=False)
    team, count = str(counts.index[0]), int(counts.iloc[0])
    return Fact(
        key="circuit_team_wins",
        value=count,
        unit="wins",
        display=f"{team}: {count} de {len(won)}",
        context=f"{team} venceu {count} das últimas {len(won)} edições em {location}.",
        source=source,
    )


def _best_brazilian(
    history: pd.DataFrame, location: str, source: Source
) -> Fact | None:
    races = history[
        (history["session"] == "race") & (history["nationality"] == BRAZILIAN)
    ].dropna(subset=["finish"])
    if races.empty:
        return None
    best = races.sort_values(["finish", "season"], ascending=[True, False]).iloc[0]
    return Fact(
        key="circuit_best_brazilian",
        value=int(best["finish"]),
        unit="position",
        display=f"P{best['finish']} ({best['name']}, {best['season']})",
        context=f"Melhor resultado de um brasileiro em {location} nas últimas "
        f"{editions(history)} edições: {best['name']} ({best['team']}), "
        f"P{best['finish']} em {best['season']}.",
        source=source,
    )


def _start_phrase(row: pd.Series) -> str:
    if bool(row["from_pit_lane"]):
        return "largando do pit lane"
    if int(row["grid"]) == 1:
        return "largando da pole"
    return f"largando de P{row['grid']}"
