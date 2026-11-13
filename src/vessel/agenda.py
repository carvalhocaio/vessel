from zoneinfo import ZoneInfo

from vessel.domain import Event, EventFormat, EventStatus, SessionKind

SESSION_LABELS = {
    SessionKind.PRACTICE_1: "TL1",
    SessionKind.PRACTICE_2: "TL2",
    SessionKind.PRACTICE_3: "TL3",
    SessionKind.SPRINT_QUALIFYING: "Quali Sprint",
    SessionKind.SPRINT: "Sprint",
    SessionKind.QUALIFYING: "Classificação",
    SessionKind.RACE: "Corrida",
}

FORMAT_LABELS = {
    EventFormat.CONVENTIONAL: "fim de semana convencional",
    EventFormat.SPRINT: "fim de semana sprint",
}

STATUS_LABELS = {
    EventStatus.AT_RISK: "Em risco",
    EventStatus.POSTPONED: "Adiado",
    EventStatus.CANCELLED: "Cancelado",
}

WEEKDAYS = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def render_agenda(event: Event, tz: ZoneInfo) -> str:
    lines = [f"{event.name} · rodada {event.round} · {FORMAT_LABELS[event.format]}"]
    if warning := status_line(event):
        lines.append(warning)
    lines.append("")
    for session in event.sessions:
        local = session.starts_at.astimezone(tz)
        when = f"{WEEKDAYS[local.weekday()]} {local:%d/%m %H:%M}"
        lines.append(
            f"{when}  {SESSION_LABELS[session.kind]}{_marker(event, session.kind)}"
        )
    lines += ["", f"Horários em {tz.key}"]
    return "\n".join(lines)


def _marker(event: Event, kind: SessionKind) -> str:
    if kind is event.long_run_session:
        return "  ← Long Run"
    if kind is SessionKind.RACE:
        return "  ← Volta Rápida"
    return ""


def status_line(event: Event) -> str | None:
    notice = event.notice
    if event.status is EventStatus.CONFIRMED or notice is None:
        return None
    line = (
        f"⚠ {STATUS_LABELS[event.status]}: {notice.note} "
        f"(atualizado em {notice.updated_on:%d/%m})"
    )
    return f"{line} · {notice.source}" if notice.source else line
