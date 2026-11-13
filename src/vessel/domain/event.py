from enum import StrEnum
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from vessel.formatting import slugify


class SessionKind(StrEnum):
    PRACTICE_1 = "fp1"
    PRACTICE_2 = "fp2"
    PRACTICE_3 = "fp3"
    SPRINT_QUALIFYING = "sprint_qualifying"
    SPRINT = "sprint"
    QUALIFYING = "qualifying"
    RACE = "race"


class EventFormat(StrEnum):
    CONVENTIONAL = "conventional"
    SPRINT = "sprint"


class Session(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: SessionKind
    starts_at: AwareDatetime
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        if self.ends_at <= self.starts_at:
            raise ValueError("a session must end after it starts")
        return self


class EventRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    season: int = Field(ge=1950)
    round: int = Field(ge=1)
    name: str = Field(min_length=1)


class Event(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    season: int = Field(ge=1950)
    round: int = Field(ge=1)
    name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    country: str = Field(min_length=1)
    format: EventFormat
    sessions: tuple[Session, ...]

    @model_validator(mode="after")
    def _sessions_are_unique_and_ordered(self) -> Self:
        kinds = [session.kind for session in self.sessions]
        if len(kinds) != len(set(kinds)):
            raise ValueError("each session kind may appear only once")
        starts = [session.starts_at for session in self.sessions]
        if starts != sorted(starts):
            raise ValueError("sessions must be in chronological order")
        return self

    @property
    def ref(self) -> EventRef:
        return EventRef(season=self.season, round=self.round, name=self.name)

    @property
    def slug(self) -> str:
        return f"{self.round:02d}-{slugify(self.location)}"

    @property
    def long_run_session(self) -> SessionKind:
        if self.format is EventFormat.SPRINT:
            return SessionKind.SPRINT
        return SessionKind.PRACTICE_2

    def session(self, kind: SessionKind) -> Session | None:
        return next((s for s in self.sessions if s.kind is kind), None)
