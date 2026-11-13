from pathlib import Path

from vessel.analytics.registry import CalcInputs, Params, chart_entry
from vessel.charts.canvas import CHARTS_DIR
from vessel.charts.render import render
from vessel.domain import (
    CHART_SPEC,
    ChartPreset,
    ChartRef,
    ChartSpec,
    Provenance,
    TableRef,
)


def save_chart(
    spec: ChartSpec,
    directory: Path,
    name: str,
    handle: str,
    *,
    provenance: Provenance,
    preset: ChartPreset = ChartPreset.X,
) -> ChartRef:
    png = render(spec, preset).save(directory, name, spec.sources, handle)
    spec_path = f"{CHARTS_DIR}/{name}.json"
    (directory / spec_path).write_bytes(CHART_SPEC.dump_json(spec, indent=2) + b"\n")
    return ChartRef(
        path=png,
        spec_path=spec_path,
        preset=preset,
        sources=spec.sources,
        provenance=provenance,
    )


def save_registered_chart(
    key: str,
    inputs: CalcInputs,
    refs: tuple[TableRef, ...],
    params: Params,
    target: tuple[Path, str, str],
) -> ChartRef:
    directory, name, handle = target
    spec = chart_entry(key)(inputs, params)
    provenance = Provenance(calculation=key, inputs=refs, params=dict(params))
    return save_chart(spec, directory, name, handle, provenance=provenance)


def load_spec(path: Path) -> ChartSpec:
    return CHART_SPEC.validate_json(path.read_bytes())
