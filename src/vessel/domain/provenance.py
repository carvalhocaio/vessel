from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from vessel.domain.event import SessionKind
from vessel.domain.regulation import Section

ParamValue = int | float | str | list[int]
CALCULATION_KEY = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SessionTableRef(_Frozen):
    kind: Literal["session"] = "session"
    season: int
    round: int
    slug: str = Field(min_length=1)
    session_kind: SessionKind


class CircuitHistoryRef(_Frozen):
    kind: Literal["circuit_history"] = "circuit_history"
    circuit_id: str = Field(min_length=1)
    before_season: int
    editions: int = Field(ge=1)


class SeasonTableRef(_Frozen):
    kind: Literal["season"] = "season"
    season: int


class RegulationTableRef(_Frozen):
    kind: Literal["regulation"] = "regulation"
    season: int
    section: Section
    issue: int = Field(ge=1)


TableRef = Annotated[
    SessionTableRef | CircuitHistoryRef | SeasonTableRef | RegulationTableRef,
    Field(discriminator="kind"),
]


class Provenance(_Frozen):
    calculation: str = Field(pattern=CALCULATION_KEY)
    inputs: tuple[TableRef, ...] = Field(min_length=1)
    params: dict[str, ParamValue] = Field(default_factory=dict)
