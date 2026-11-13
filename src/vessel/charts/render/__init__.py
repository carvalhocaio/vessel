from vessel.charts.canvas import Chart
from vessel.charts.render.grid_timeline import render_grid_timeline
from vessel.charts.render.position_lines import render_position_lines
from vessel.charts.render.ranged_dots import render_ranged_dots
from vessel.charts.render.ranked_dots import render_ranked_dots
from vessel.charts.render.stint_bars import render_stint_bars
from vessel.domain import (
    ChartPreset,
    ChartSpec,
    GridTimelineSpec,
    PositionLinesSpec,
    RangedDotsSpec,
    RankedDotsSpec,
    StintBarsSpec,
)


def render(spec: ChartSpec, preset: ChartPreset = ChartPreset.X) -> Chart:
    match spec:
        case StintBarsSpec():
            return render_stint_bars(spec, preset)
        case PositionLinesSpec():
            return render_position_lines(spec, preset)
        case RangedDotsSpec():
            return render_ranged_dots(spec, preset)
        case GridTimelineSpec():
            return render_grid_timeline(spec, preset)
        case RankedDotsSpec():
            return render_ranked_dots(spec, preset)


__all__ = ["render"]
