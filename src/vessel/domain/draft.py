from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from vessel.domain.event import EventRef

SCHEMA_VERSION: Literal[1] = 1


class Source(StrEnum):
    FASTF1 = "FastF1"
    JOLPICA = "Jolpica"
    FIA = "FIA"


class Segment(StrEnum):
    CIRCUIT_PREVIEW = "circuit_preview"
    LONG_RUN = "long_run"
    RACE_RECAP = "race_recap"
    REGULATIONS = "regulations"
    TELEMETRY = "telemetry"


class ChartPreset(StrEnum):
    X = "x"
    FEED = "feed"
    STORY = "story"


class Fact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    value: int | float | str
    unit: str | None = None
    display: str = Field(min_length=1)
    context: str = Field(min_length=1)
    source: Source


class ChartRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    preset: ChartPreset
    sources: tuple[Source, ...] = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def _relative_inside_draft(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or not path.suffix:
            raise ValueError("chart path must be a relative file inside the draft")
        return value


class Draft(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    segment: Segment
    event: EventRef
    facts: tuple[Fact, ...] = Field(min_length=1)
    caveats: tuple[str, ...] = ()
    charts: tuple[ChartRef, ...] = ()
    generated_at: AwareDatetime

    @model_validator(mode="after")
    def _fact_keys_are_unique(self) -> Self:
        keys = [fact.key for fact in self.facts]
        if len(keys) != len(set(keys)):
            raise ValueError("fact keys must be unique within a draft")
        return self

    @property
    def sources(self) -> tuple[Source, ...]:
        used = {fact.source for fact in self.facts}
        used.update(source for chart in self.charts for source in chart.sources)
        return tuple(source for source in Source if source in used)
