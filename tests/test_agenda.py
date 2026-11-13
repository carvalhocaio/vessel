from zoneinfo import ZoneInfo

from vessel.agenda import render_agenda
from vessel.domain import Event, EventFormat

CUIABA = ZoneInfo("America/Cuiaba")


def _by_round(events: tuple[Event, ...], round_: int) -> Event:
    return next(event for event in events if event.round == round_)


def test_renders_las_vegas_in_cuiaba_time(schedule_2026: tuple[Event, ...]) -> None:
    lines = render_agenda(_by_round(schedule_2026, 21), CUIABA).splitlines()

    assert lines[0] == "Las Vegas Grand Prix · rodada 21 · fim de semana convencional"
    assert "qui 19/11 20:30  TL1" in lines
    assert "sex 20/11 00:00  TL2  ← Long Run" in lines
    assert "dom 22/11 00:00  Corrida  ← Volta Rápida" in lines
    assert lines[-1] == "Horários em America/Cuiaba"


def test_sprint_weekend_marks_sprint_as_long_run(
    schedule_2026: tuple[Event, ...],
) -> None:
    china = _by_round(schedule_2026, 2)

    output = render_agenda(china, CUIABA)

    assert china.format is EventFormat.SPRINT
    assert "Sprint  ← Long Run" in output
    assert "fim de semana sprint" in output
