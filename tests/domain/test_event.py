from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from tests.factories import make_session
from vessel.domain import Event, EventFormat, EventRef, Session, SessionKind

START = datetime(2027, 3, 14, 5, 0, tzinfo=UTC)


def test_slug_combines_round_and_location(sao_paulo: Event) -> None:
    assert sao_paulo.slug == "21-sao-paulo"


def test_ref_keeps_identity_only(sao_paulo: Event) -> None:
    assert sao_paulo.ref == EventRef(season=2026, round=21, name="São Paulo Grand Prix")


def test_session_lookup(sao_paulo: Event) -> None:
    race = sao_paulo.session(SessionKind.RACE)

    assert race is not None
    assert race.starts_at == datetime(2026, 11, 8, 17, 0, tzinfo=UTC)
    assert sao_paulo.session(SessionKind.SPRINT) is None


def test_long_run_comes_from_fp2_on_conventional_weekend(sao_paulo: Event) -> None:
    assert sao_paulo.long_run_session is SessionKind.PRACTICE_2


def test_long_run_comes_from_sprint_on_sprint_weekend(sao_paulo: Event) -> None:
    sprint_weekend = sao_paulo.model_copy(update={"format": EventFormat.SPRINT})

    assert sprint_weekend.long_run_session is SessionKind.SPRINT


def test_session_must_end_after_start() -> None:
    with pytest.raises(ValidationError, match="end after it starts"):
        Session(kind=SessionKind.RACE, starts_at=START, ends_at=START)


def test_session_rejects_naive_datetimes() -> None:
    with pytest.raises(ValidationError):
        Session(
            kind=SessionKind.RACE,
            starts_at=datetime(2027, 3, 14, 5, 0),
            ends_at=datetime(2027, 3, 14, 7, 0),
        )


def _event(*sessions: Session) -> Event:
    return Event(
        season=2027,
        round=1,
        name="Australian Grand Prix",
        location="Melbourne",
        country="Australia",
        format=EventFormat.CONVENTIONAL,
        sessions=sessions,
    )


def test_event_rejects_duplicated_session_kind() -> None:
    race = make_session(SessionKind.RACE, START)

    with pytest.raises(ValidationError, match="only once"):
        _event(race, race)


def test_event_rejects_sessions_out_of_order() -> None:
    quali = make_session(SessionKind.QUALIFYING, START.replace(day=13))
    race = make_session(SessionKind.RACE, START)

    with pytest.raises(ValidationError, match="chronological"):
        _event(race, quali)
