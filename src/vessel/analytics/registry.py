from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import pandas as pd

from vessel.curation.schema import RaceTables, SeasonTables, SessionTables
from vessel.domain import ChartSpec, Fact, ParamValue, Provenance, Source, TableRef

Params = Mapping[str, ParamValue]
RegulationKey = tuple[int, str, int]


class CalculationError(ValueError):
    pass


class MissingInputError(CalculationError):
    pass


@dataclass(frozen=True, slots=True)
class Finding:
    key: str
    value: int | float | str
    display: str
    context: str
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class CalcInputs:
    race_tables: RaceTables | None = None
    session_tables: SessionTables | None = None
    history_table: pd.DataFrame | None = None
    season_tables: SeasonTables | None = None
    regulation_tables: Mapping[RegulationKey, pd.DataFrame] = field(
        default_factory=dict
    )

    def regulation(self, season: int, section: str, issue: int) -> pd.DataFrame:
        key = (season, section, issue)
        if key not in self.regulation_tables:
            raise MissingInputError(f"missing regulation articles {key}")
        return self.regulation_tables[key]

    @property
    def race(self) -> RaceTables:
        return _required(self.race_tables, "race session tables")

    @property
    def session(self) -> SessionTables:
        return _required(self.session_tables, "session tables")

    @property
    def history(self) -> pd.DataFrame:
        return _required(self.history_table, "circuit history table")

    @property
    def season(self) -> SeasonTables:
        return _required(self.season_tables, "season tables")


FactCalculation = Callable[[CalcInputs, Params], Finding | None]
ChartCalculation = Callable[[CalcInputs, Params], ChartSpec]


@dataclass(frozen=True, slots=True)
class FactEntry:
    key: str
    source: Source
    compute: FactCalculation


FACTS: dict[str, FactEntry] = {}
CHARTS: dict[str, ChartCalculation] = {}


def calculation(
    key: str, source: Source
) -> Callable[[FactCalculation], FactCalculation]:
    def register(compute: FactCalculation) -> FactCalculation:
        _ensure_new(key)
        FACTS[key] = FactEntry(key=key, source=source, compute=compute)
        return compute

    return register


def chart_calculation(key: str) -> Callable[[ChartCalculation], ChartCalculation]:
    def register(compute: ChartCalculation) -> ChartCalculation:
        _ensure_new(key)
        CHARTS[key] = compute
        return compute

    return register


def fact_entry(key: str) -> FactEntry:
    try:
        return FACTS[key]
    except KeyError:
        raise CalculationError(f"calculation {key!r} is not registered") from None


def chart_entry(key: str) -> ChartCalculation:
    try:
        return CHARTS[key]
    except KeyError:
        raise CalculationError(f"chart {key!r} is not registered") from None


def compute_facts(
    keys: tuple[str, ...],
    inputs: CalcInputs,
    refs: tuple[TableRef, ...],
    params: Params,
) -> tuple[Fact, ...]:
    facts = []
    for key in keys:
        entry = fact_entry(key)
        finding = entry.compute(inputs, params)
        if finding is None:
            continue
        facts.append(
            Fact(
                key=finding.key,
                value=finding.value,
                unit=finding.unit,
                display=finding.display,
                context=finding.context,
                source=entry.source,
                provenance=Provenance(
                    calculation=key, inputs=refs, params=dict(params)
                ),
            )
        )
    return tuple(facts)


def int_param(params: Params, name: str) -> int:
    value = _param(params, name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CalculationError(f"parameter {name!r} must be an integer")
    return value


def float_param(params: Params, name: str) -> float:
    value = _param(params, name)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CalculationError(f"parameter {name!r} must be a number")
    return float(value)


def str_param(params: Params, name: str) -> str:
    value = _param(params, name)
    if not isinstance(value, str):
        raise CalculationError(f"parameter {name!r} must be a string")
    return value


def int_list_param(params: Params, name: str) -> list[int]:
    value = _param(params, name)
    if not isinstance(value, list):
        raise CalculationError(f"parameter {name!r} must be a list of integers")
    return value


def _param(params: Params, name: str) -> ParamValue:
    try:
        return params[name]
    except KeyError:
        raise CalculationError(f"missing parameter {name!r}") from None


def _ensure_new(key: str) -> None:
    if key in FACTS or key in CHARTS:
        raise CalculationError(f"calculation {key!r} is already registered")


def _required[T](value: T | None, name: str) -> T:
    if value is None:
        raise MissingInputError(f"missing {name}")
    return value
