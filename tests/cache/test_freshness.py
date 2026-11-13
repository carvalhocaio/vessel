from datetime import UTC, datetime, timedelta

import pytest

from vessel.cache import TIMING_SETTLE, Forever, ParcFerme, Ttl
from vessel.domain import Event, SessionKind

T0 = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)


def test_forever_is_always_fresh() -> None:
    assert Forever().is_fresh(T0, T0 + timedelta(days=3650))


@pytest.mark.parametrize(
    ("age", "fresh"), [(timedelta(0), True), (HOUR - timedelta(seconds=1), True)]
)
def test_ttl_inside_window(age: timedelta, fresh: bool) -> None:
    assert Ttl(HOUR).is_fresh(T0, T0 + age) is fresh


def test_ttl_expires_at_max_age() -> None:
    assert not Ttl(HOUR).is_fresh(T0, T0 + HOUR)


class TestParcFerme:
    policy = ParcFerme(locked_at=T0, in_flux=Ttl(timedelta(minutes=15)))

    def test_entry_written_after_lock_never_expires(self) -> None:
        assert self.policy.is_fresh(T0 + HOUR, T0 + timedelta(days=365))

    def test_entry_written_before_lock_is_stale_once_locked(self) -> None:
        assert not self.policy.is_fresh(T0 - timedelta(minutes=1), T0)

    def test_entry_in_flux_uses_short_ttl(self) -> None:
        written = T0 - HOUR

        assert self.policy.is_fresh(written, written + timedelta(minutes=10))
        assert not self.policy.is_fresh(written, written + timedelta(minutes=20))

    def test_after_session_locks_once_data_settles(self, sao_paulo: Event) -> None:
        race = sao_paulo.session(SessionKind.RACE)
        assert race is not None

        policy = ParcFerme.after(race)

        assert policy.locked_at == race.ends_at + TIMING_SETTLE
