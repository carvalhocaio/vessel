from datetime import date
from zoneinfo import ZoneInfo

from pydantic import HttpUrl

from vessel.agenda import render_agenda, status_line
from vessel.domain import Event, EventFormat, EventNotice, EventStatus

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


def test_agenda_warns_when_gp_is_not_confirmed(
    schedule_2026: tuple[Event, ...],
) -> None:
    notice = EventNotice(
        status=EventStatus.AT_RISK,
        note="conflitos na região",
        updated_on=date(2026, 11, 13),
    )
    qatar = _by_round(schedule_2026, 22).with_notice(notice)

    lines = render_agenda(qatar, CUIABA).splitlines()

    assert lines[1] == "⚠ Em risco: conflitos na região (atualizado em 13/11)"


def test_agenda_warning_includes_source_link(
    schedule_2026: tuple[Event, ...],
) -> None:
    notice = EventNotice(
        status=EventStatus.CANCELLED,
        note="evento cancelado",
        source=HttpUrl("https://www.formula1.com/en/latest"),
        updated_on=date(2026, 11, 10),
    )

    line = status_line(_by_round(schedule_2026, 22).with_notice(notice))

    assert line == (
        "⚠ Cancelado: evento cancelado (atualizado em 10/11) · "
        "https://www.formula1.com/en/latest"
    )


def test_confirmed_gp_has_no_warning(schedule_2026: tuple[Event, ...]) -> None:
    lines = render_agenda(_by_round(schedule_2026, 21), CUIABA).splitlines()

    assert status_line(_by_round(schedule_2026, 21)) is None
    assert lines[1] == ""
