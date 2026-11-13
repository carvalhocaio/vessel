from pathlib import Path

import pytest

from tests.factories import FIXTURES
from vessel.domain import Event, EventStatus
from vessel.event_status import EventStatusFile, EventStatusFileError, load_event_status

VALID = FIXTURES / "event_status.toml"


def write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "event_status.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_loads_notices_indexed_by_season_and_round() -> None:
    notices = load_event_status(VALID).notices(2026)

    assert notices[22].status is EventStatus.AT_RISK
    assert notices[22].note == "conflitos na região"
    assert notices[22].source is None
    assert str(notices[21].source) == "https://www.formula1.com/en/latest"


def test_missing_file_is_an_empty_registry(tmp_path: Path) -> None:
    assert load_event_status(tmp_path / "absent.toml").notices(2026) == {}


def test_broken_toml_fails_with_path(tmp_path: Path) -> None:
    path = write(tmp_path, "[2026.22\nstatus = 'at_risk'")

    with pytest.raises(EventStatusFileError, match=r"event_status\.toml: invalid TOML"):
        load_event_status(path)


def test_invalid_status_names_the_field(tmp_path: Path) -> None:
    path = write(
        tmp_path,
        '[2026.22]\nstatus = "maybe"\nnote = "x"\nupdated_on = 2026-11-13\n',
    )

    with pytest.raises(EventStatusFileError, match=r"2026\.22\.status"):
        load_event_status(path)


def test_missing_note_is_rejected(tmp_path: Path) -> None:
    path = write(tmp_path, '[2026.22]\nstatus = "at_risk"\nupdated_on = 2026-11-13\n')

    with pytest.raises(EventStatusFileError, match=r"2026\.22\.note"):
        load_event_status(path)


def test_applies_notices_to_events(schedule_2026: tuple[Event, ...]) -> None:
    events = EventStatusFile(VALID).apply(schedule_2026)

    by_round = {event.round: event for event in events}
    assert by_round[21].is_cancelled
    assert by_round[22].status is EventStatus.AT_RISK
    assert by_round[22].notice is not None
    assert by_round[20].status is EventStatus.CONFIRMED
    assert by_round[20].notice is None


def test_unknown_round_fails_when_applied(
    tmp_path: Path, schedule_2026: tuple[Event, ...]
) -> None:
    path = write(
        tmp_path,
        '[2026.99]\nstatus = "at_risk"\nnote = "x"\nupdated_on = 2026-11-13\n',
    )

    with pytest.raises(EventStatusFileError, match="2026 round 99 does not exist"):
        EventStatusFile(path).apply(schedule_2026)


def test_absent_file_leaves_events_untouched(schedule_2026: tuple[Event, ...]) -> None:
    status = EventStatusFile(FIXTURES / "absent.toml")

    assert status.apply(schedule_2026) == schedule_2026
