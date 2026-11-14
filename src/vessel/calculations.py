from types import ModuleType

from vessel.analytics import circuit_history, form, long_run, race, regulations
from vessel.charts.specs import circuit_preview
from vessel.charts.specs import long_run as long_run_chart
from vessel.charts.specs import race as race_chart

MODULES: tuple[ModuleType, ...] = (
    race,
    long_run,
    circuit_history,
    form,
    regulations,
    race_chart,
    long_run_chart,
    circuit_preview,
)


def load_calculations() -> tuple[ModuleType, ...]:
    return MODULES
