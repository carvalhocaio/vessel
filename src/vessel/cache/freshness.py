from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol, Self

from vessel.domain.event import Session

TIMING_SETTLE = timedelta(hours=2)
RESULTS_SETTLE = timedelta(hours=24)


class Freshness(Protocol):
    def is_fresh(self, written_at: datetime, now: datetime) -> bool: ...


@dataclass(frozen=True, slots=True)
class Forever:
    def is_fresh(self, written_at: datetime, now: datetime) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class Ttl:
    max_age: timedelta

    def is_fresh(self, written_at: datetime, now: datetime) -> bool:
        return now - written_at < self.max_age


@dataclass(frozen=True, slots=True)
class ParcFerme:
    locked_at: datetime
    in_flux: Ttl = field(default_factory=lambda: Ttl(timedelta(minutes=15)))

    @classmethod
    def after(cls, session: Session, settle: timedelta = TIMING_SETTLE) -> Self:
        return cls(locked_at=session.ends_at + settle)

    def is_fresh(self, written_at: datetime, now: datetime) -> bool:
        if written_at >= self.locked_at:
            return True
        if now >= self.locked_at:
            return False
        return self.in_flux.is_fresh(written_at, now)
