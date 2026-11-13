import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from vessel.analytics.registry import (
    CalcInputs,
    CalculationError,
    chart_entry,
    fact_entry,
)
from vessel.calculations import load_calculations
from vessel.charts.output import load_spec
from vessel.curation.tables import TableLoader
from vessel.domain import CHART_SPEC, ChartRef, Draft, Fact, TableRef

FLOAT_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class Check:
    item: str
    saved: str
    recomputed: str
    ok: bool


@dataclass(frozen=True, slots=True)
class VerificationReport:
    checks: tuple[Check, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def failures(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if not check.ok)


def load_draft(path: Path) -> Draft:
    return Draft.model_validate_json(path.read_text(encoding="utf-8"))


def verify_file(path: Path, loader: TableLoader) -> VerificationReport:
    return verify_draft(load_draft(path), path.parent, loader)


def verify_draft(
    draft: Draft, directory: Path, loader: TableLoader
) -> VerificationReport:
    load_calculations()
    load = _memoized(loader)
    checks = [_check_fact(fact, load) for fact in draft.facts]
    checks += [_check_chart(chart, directory, load) for chart in draft.charts]
    return VerificationReport(tuple(checks))


def verifier(loader: TableLoader) -> Callable[[Draft, Path], tuple[str, ...]]:
    def verify(draft: Draft, directory: Path) -> tuple[str, ...]:
        report = verify_draft(draft, directory, loader)
        return tuple(
            f"{check.item}: salvo {check.saved}, recalculado {check.recomputed}"
            for check in report.failures
        )

    return verify


def same_value(saved: object, recomputed: object) -> bool:
    if isinstance(saved, bool) or isinstance(recomputed, bool):
        return saved == recomputed and type(saved) is type(recomputed)
    if isinstance(saved, float) or isinstance(recomputed, float):
        if not (isinstance(saved, float) and isinstance(recomputed, float)):
            return False
        return math.isclose(saved, recomputed, rel_tol=0, abs_tol=FLOAT_TOLERANCE)
    if isinstance(saved, dict) and isinstance(recomputed, dict):
        return saved.keys() == recomputed.keys() and all(
            same_value(saved[key], recomputed[key]) for key in saved
        )
    if isinstance(saved, list) and isinstance(recomputed, list):
        return len(saved) == len(recomputed) and all(
            same_value(a, b) for a, b in zip(saved, recomputed, strict=True)
        )
    return type(saved) is type(recomputed) and saved == recomputed


Loader = Callable[[tuple[TableRef, ...]], CalcInputs]


def _memoized(loader: TableLoader) -> Loader:
    cache: dict[tuple[TableRef, ...], CalcInputs] = {}

    def load(refs: tuple[TableRef, ...]) -> CalcInputs:
        if refs not in cache:
            cache[refs] = loader.load(refs)
        return cache[refs]

    return load


def _check_fact(fact: Fact, load: Loader) -> Check:
    saved = f"{fact.value!r} · {fact.display}"
    provenance = fact.provenance
    try:
        entry = fact_entry(provenance.calculation)
    except CalculationError as exc:
        return Check(fact.key, saved, str(exc), ok=False)
    finding = entry.compute(load(provenance.inputs), provenance.params)
    if finding is None or finding.key != fact.key:
        return Check(fact.key, saved, "não recalculável", ok=False)
    recomputed = f"{finding.value!r} · {finding.display}"
    ok = same_value(fact.value, finding.value) and fact.display == finding.display
    return Check(fact.key, saved, recomputed, ok=ok)


def _check_chart(chart: ChartRef, directory: Path, load: Loader) -> Check:
    item = f"chart {chart.spec_path}"
    provenance = chart.provenance
    try:
        build = chart_entry(provenance.calculation)
        saved = load_spec(directory / chart.spec_path)
    except (CalculationError, FileNotFoundError, ValueError) as exc:
        return Check(item, "—", str(exc), ok=False)
    spec = build(load(provenance.inputs), provenance.params)
    saved_doc = json.loads(CHART_SPEC.dump_json(saved))
    recomputed_doc = json.loads(CHART_SPEC.dump_json(spec))
    ok = same_value(saved_doc, recomputed_doc)
    return Check(
        item,
        saved.kind,
        spec.kind if ok else f"{spec.kind} (spec diverge)",
        ok=ok,
    )
