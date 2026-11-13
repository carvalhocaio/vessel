from dataclasses import dataclass

import pandas as pd

from vessel.analytics.registry import CalcInputs, Finding, Params, calculation
from vessel.domain import Source
from vessel.formatting import compound_name, format_decimal, format_lap_time

NEUTRALISED_STATUSES = frozenset("4567")
GRID_LAP = 0
BRAZILIAN = "Brazilian"
PODIUM = 3


@dataclass(frozen=True, slots=True)
class Classified:
    driver: str
    name: str
    team: str
    grid: int
    finish: int
    from_pit_lane: bool

    @property
    def change(self) -> int:
        return self.grid - self.finish


def clean_laps(laps: pd.DataFrame) -> pd.DataFrame:
    neutralised = (
        laps["track_status"]
        .fillna("")
        .map(lambda status: bool(NEUTRALISED_STATUSES.intersection(status)))
    )
    mask = (
        laps["is_accurate"].fillna(value=False)
        & ~laps["pit_in"].fillna(value=False)
        & ~laps["pit_out"].fillna(value=False)
        & (laps["lap"] > 1)
        & laps["lap_time_s"].notna()
        & ~neutralised.astype(bool)
    )
    return laps[mask.astype(bool)]


def stint_summary(laps: pd.DataFrame) -> pd.DataFrame:
    stints = laps.dropna(subset=["stint"])
    summary = (
        stints.sort_values("lap")
        .groupby(["driver", "stint"], as_index=False)
        .agg(
            compound=("compound", "first"),
            compound_color=("compound_color", "first"),
            lap_start=("lap", "min"),
            lap_end=("lap", "max"),
            laps=("lap", "count"),
        )
    )
    return summary.sort_values(["driver", "stint"]).reset_index(drop=True)


def finishing_order(results: pd.DataFrame, laps: pd.DataFrame) -> list[str]:
    raced = set(laps["driver"])
    ordered = results.sort_values("finish", na_position="last")
    return [str(driver) for driver in ordered["driver"] if driver in raced]


def starters(results: pd.DataFrame, laps: pd.DataFrame) -> int:
    return len(finishing_order(results, laps))


def positions_by_lap(laps: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    order = finishing_order(results, laps)
    back_of_grid = len(order)
    grid = results[results["driver"].isin(order)]
    start = pd.DataFrame(
        {
            "driver": grid["driver"],
            "lap": GRID_LAP,
            "position": grid["grid"].fillna(back_of_grid),
        }
    )
    running = laps.dropna(subset=["position"])[["driver", "lap", "position"]]
    positions = pd.concat([start, running], ignore_index=True)
    positions = positions.astype({"lap": "Int16", "position": "Int16"})
    return positions.sort_values(["driver", "lap"]).reset_index(drop=True)


def classified(results: pd.DataFrame, laps: pd.DataFrame) -> list[Classified]:
    back_of_grid = starters(results, laps)
    rows = results[results["classified"].fillna(value=False).astype(bool)]
    return [
        Classified(
            driver=str(row["driver"]),
            name=str(row["name"]),
            team=str(row["team"]),
            grid=back_of_grid if pd.isna(row["grid"]) else int(row["grid"]),
            finish=int(row["finish"]),
            from_pit_lane=bool(pd.isna(row["grid"])),
        )
        for row in rows.sort_values("finish").to_dict("records")
    ]


def winner(results: pd.DataFrame) -> str:
    return str(results.sort_values("finish")["driver"].iloc[0])


def driver_names(results: pd.DataFrame) -> dict[str, str]:
    return {
        str(driver): str(name) if pd.notna(name) and name else str(driver)
        for driver, name in zip(results["driver"], results["name"], strict=True)
    }


def pit_stops(laps: pd.DataFrame, driver: str) -> int:
    stints = laps.loc[laps["driver"] == driver, "stint"].dropna()
    return max(stints.nunique() - 1, 0)


def highlighted_drivers(results: pd.DataFrame) -> set[str]:
    ordered = results.sort_values("finish")
    podium = ordered.head(PODIUM)["driver"]
    brazilians = ordered.loc[ordered["nationality"] == BRAZILIAN, "driver"]
    return {str(driver) for driver in (*podium, *brazilians)}


RACE_FACTS = (
    "race.biggest_gain",
    "race.biggest_loss",
    "race.longest_stint",
    "race.fastest_lap",
    "race.winner_pace_gap_p2",
    "race.winner_pit_stops",
)


@calculation("race.biggest_gain", Source.FASTF1)
def biggest_gain(inputs: CalcInputs, params: Params) -> Finding | None:
    laps, results = inputs.race.laps, inputs.race.results
    gainers = [entry for entry in classified(results, laps) if entry.change > 0]
    if not gainers:
        return None
    best = max(gainers, key=lambda entry: (entry.change, -entry.finish))
    return Finding(
        key="biggest_gain",
        value=best.change,
        unit="positions",
        display=f"+{best.change} posições",
        context=f"{best.name} ({best.team}) {_start_phrase(best)} e terminou em "
        f"P{best.finish}; maior ganho entre os classificados.",
    )


@calculation("race.biggest_loss", Source.FASTF1)
def biggest_loss(inputs: CalcInputs, params: Params) -> Finding | None:
    laps, results = inputs.race.laps, inputs.race.results
    losers = [entry for entry in classified(results, laps) if entry.change < 0]
    if not losers:
        return None
    worst = min(losers, key=lambda entry: (entry.change, -entry.finish))
    return Finding(
        key="biggest_loss",
        value=worst.change,
        unit="positions",
        display=f"{worst.change} posições",
        context=f"{worst.name} ({worst.team}) {_start_phrase(worst)} e terminou em "
        f"P{worst.finish}; maior perda entre os classificados.",
    )


@calculation("race.longest_stint", Source.FASTF1)
def longest_stint(inputs: CalcInputs, params: Params) -> Finding | None:
    laps, results = inputs.race.laps, inputs.race.results
    stints = stint_summary(laps)
    if stints.empty:
        return None
    finish = results.set_index("driver")["finish"]
    stints = stints.assign(finish=stints["driver"].map(finish))
    best = stints.sort_values(["laps", "finish"], ascending=[False, True]).iloc[0]
    compound = compound_name(str(best["compound"]))
    name = driver_names(results).get(str(best["driver"]), str(best["driver"]))
    return Finding(
        key="longest_stint",
        value=int(best["laps"]),
        unit="laps",
        display=f"{int(best['laps'])} voltas",
        context=f"{name} ficou {int(best['laps'])} voltas com o pneu "
        f"{compound}, da volta {int(best['lap_start'])} à {int(best['lap_end'])}; "
        "stint mais longo da corrida.",
    )


@calculation("race.fastest_lap", Source.FASTF1)
def fastest_lap(inputs: CalcInputs, params: Params) -> Finding | None:
    laps, results = inputs.race.laps, inputs.race.results
    timed = laps.dropna(subset=["lap_time_s"])
    if timed.empty:
        return None
    best = timed.sort_values(["lap_time_s", "lap"]).iloc[0]
    seconds = float(best["lap_time_s"])
    name = driver_names(results).get(str(best["driver"]), str(best["driver"]))
    tyre = f"pneu {compound_name(str(best['compound']))}"
    if pd.notna(best["tyre_life"]):
        tyre += f" de {int(best['tyre_life'])} voltas"
    return Finding(
        key="fastest_lap",
        value=round(seconds, 3),
        unit="s",
        display=format_lap_time(seconds),
        context=f"{name} fez a volta mais rápida na volta {int(best['lap'])}, "
        f"com {tyre}.",
    )


@calculation("race.winner_pace_gap_p2", Source.FASTF1)
def winner_pace_gap_p2(inputs: CalcInputs, params: Params) -> Finding | None:
    laps, results = inputs.race.laps, inputs.race.results
    ordered = results[results["classified"].fillna(value=False).astype(bool)]
    ordered = ordered.sort_values("finish")
    if len(ordered) < 2:  # noqa: PLR2004
        return None
    first, second = (str(driver) for driver in ordered["driver"].iloc[:2])
    names = driver_names(results)
    clean = clean_laps(laps)
    first_laps = clean.loc[clean["driver"] == first, "lap_time_s"]
    second_laps = clean.loc[clean["driver"] == second, "lap_time_s"]
    if first_laps.empty or second_laps.empty:
        return None
    gap = float(second_laps.median()) - float(first_laps.median())
    faster = first if gap >= 0 else second
    return Finding(
        key="winner_pace_gap_p2",
        value=round(gap, 3),
        unit="s/lap",
        display=f"{format_decimal(abs(gap), 3)} s/volta",
        context=f"Mediana das voltas limpas: {names[first]} "
        f"{format_lap_time(float(first_laps.median()))} ({len(first_laps)} voltas) "
        f"contra {names[second]} {format_lap_time(float(second_laps.median()))} "
        f"({len(second_laps)} voltas); {names[faster]} foi mais rápido.",
    )


@calculation("race.winner_pit_stops", Source.FASTF1)
def winner_pit_stops(inputs: CalcInputs, params: Params) -> Finding | None:
    laps, results = inputs.race.laps, inputs.race.results
    driver = winner(results)
    if driver not in set(laps["driver"]):
        return None
    stops = pit_stops(laps, driver)
    compounds = stint_summary(laps).query("driver == @driver")["compound"]
    sequence = " → ".join(compound_name(str(compound)) for compound in compounds)
    noun = "parada" if stops == 1 else "paradas"
    return Finding(
        key="winner_pit_stops",
        value=stops,
        unit="stops",
        display=f"{stops} {noun}",
        context=f"{driver_names(results)[driver]} venceu com {stops} {noun} "
        f"({sequence}).",
    )


def _start_phrase(entry: Classified) -> str:
    if entry.from_pit_lane:
        return "largou do pit lane"
    return f"largou em P{entry.grid}"
