import pandas as pd

from vessel.analytics.form import recent_form
from vessel.analytics.long_run import long_runs
from vessel.analytics.race import positions_by_lap, stint_summary
from vessel.charts.specs.circuit_preview import grid_timeline_spec, ranked_dots_spec
from vessel.charts.specs.long_run import ranged_dots_spec
from vessel.charts.specs.race import position_lines_spec, stint_bars_spec
from vessel.curation import RaceTables, SeasonTables, SessionTables
from vessel.domain import AxisFormat, SessionKind, Source


def test_stint_bars_from_recorded_race(race_2026_20: RaceTables) -> None:
    laps, results = race_2026_20.laps, race_2026_20.results

    spec = stint_bars_spec(stint_summary(laps), laps, results)

    assert spec.title == "Norris venceu com 3 paradas"
    assert spec.subtitle == (
        "Stints em ordem de chegada · S macio, INT intermediário · voltas"
    )
    assert spec.sources == (Source.FASTF1,)
    assert [series.id for series in spec.series][:3] == ["NOR", "VER", "HAD"]
    assert "BOT" not in {series.id for series in spec.series}
    norris = spec.series[0]
    assert [segment.category_label for segment in norris.segments] == [
        "INT",
        "S",
        "S",
        "INT",
    ]
    assert norris.segments[0].start_lap == 1
    assert sum(segment.laps for segment in norris.segments) == 71
    assert [entry.code for entry in spec.legend] == ["S", "INT"]
    assert spec.x.domain == (0, 71)


def test_position_lines_from_recorded_race(race_2026_20: RaceTables) -> None:
    laps, results = race_2026_20.laps, race_2026_20.results

    spec = position_lines_spec(positions_by_lap(laps, results), laps, results)

    assert spec.title == "Norris largou na pole e venceu"
    by_id = {series.id: series for series in spec.series}
    highlighted = {series.id for series in spec.series if series.highlighted}
    assert highlighted == {"NOR", "VER", "HAD", "BOR", "CAM"}
    assert by_id["HAD"].dashed
    assert not by_id["VER"].dashed
    assert by_id["VER"].points[0].position == 21
    assert by_id["NOR"].color == "#ff8000"
    assert spec.y.inverted
    assert spec.y.domain == (1, 21)


def test_ranged_dots_from_recorded_fp2(fp2_2026_20: SessionTables) -> None:
    runs = long_runs(fp2_2026_20.laps, fp2_2026_20.drivers)

    spec = ranged_dots_spec(runs, SessionKind.PRACTICE_2)

    assert spec.title == "Mercedes tem o melhor ritmo no TL2"
    leader = spec.series[0]
    assert leader.detail_label == "ANT · macio · 17 voltas"
    assert leader.point.value_label == "1:15,404"
    assert leader.point.low <= leader.point.value <= leader.point.high
    assert spec.x.format is AxisFormat.LAP_TIME


def test_grid_timeline_from_interlagos(interlagos_history: pd.DataFrame) -> None:
    spec = grid_timeline_spec(interlagos_history, "São Paulo")

    assert spec.title == "A pole venceu 7 das últimas 10 em São Paulo"
    points = {point.season: point for point in spec.series[0].points}
    assert points[2024].start == 17
    assert points[2024].start_label == "P17"
    assert points[2024].label == "VER"
    assert spec.y.domain == (1, 17)


def test_ranked_dots_from_season(season_2026: SeasonTables) -> None:
    form = recent_form(season_2026.results)

    spec = ranked_dots_spec(form, season_2026.standings, {"VER": "#0600ef"})

    assert spec.title == "Verstappen chega em melhor forma"
    assert len(spec.series) == 10
    assert spec.series[0].detail_label == "VER · 1,6"
    assert spec.series[0].color == "#0600ef"
    assert spec.series[1].color is None
