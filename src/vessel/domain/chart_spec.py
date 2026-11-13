from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from vessel.domain.draft import Source


class AxisFormat(StrEnum):
    LAP_TIME = "lap_time"
    DECIMAL = "decimal"
    INTEGER = "integer"
    POSITION = "position"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Axis(_Frozen):
    label: str | None = None
    unit: str | None = None
    format: AxisFormat
    inverted: bool = False
    domain: tuple[float, float] | None = None


class _Series(_Frozen):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    color: str | None = None
    highlighted: bool = False


class _ChartBase(_Frozen):
    title: str = Field(min_length=1)
    subtitle: str | None = None
    sources: tuple[Source, ...] = Field(min_length=1)
    x: Axis
    y: Axis


class StintSegment(_Frozen):
    start_lap: int = Field(ge=1)
    end_lap: int = Field(ge=1)
    laps: int = Field(ge=1)
    category: str
    category_label: str
    color: str | None = None


class StintSeries(_Series):
    segments: tuple[StintSegment, ...]


class LegendEntry(_Frozen):
    code: str
    label: str
    color: str | None = None


class StintBarsSpec(_ChartBase):
    kind: Literal["stint_bars"] = "stint_bars"
    series: tuple[StintSeries, ...]
    legend: tuple[LegendEntry, ...] = ()


class PositionPoint(_Frozen):
    lap: int = Field(ge=0)
    position: int = Field(ge=1)


class PositionSeries(_Series):
    points: tuple[PositionPoint, ...] = Field(min_length=1)
    end_label: str
    dashed: bool = False


class PositionLinesSpec(_ChartBase):
    kind: Literal["position_lines"] = "position_lines"
    series: tuple[PositionSeries, ...]


class RangedPoint(_Frozen):
    value: float
    low: float
    high: float
    value_label: str
    range_label: str


class RangedSeries(_Series):
    point: RangedPoint
    detail_label: str


class RangedDotsSpec(_ChartBase):
    kind: Literal["ranged_dots"] = "ranged_dots"
    series: tuple[RangedSeries, ...] = Field(min_length=1)


class TimelinePoint(_Frozen):
    season: int
    start: int = Field(ge=1)
    from_pit_lane: bool = False
    driver: str
    label: str
    start_label: str


class TimelineSeries(_Series):
    points: tuple[TimelinePoint, ...] = Field(min_length=1)


class GridTimelineSpec(_ChartBase):
    kind: Literal["grid_timeline"] = "grid_timeline"
    series: tuple[TimelineSeries, ...] = Field(min_length=1)


class RankedPoint(_Frozen):
    value: float
    value_label: str


class RankedSeries(_Series):
    point: RankedPoint
    detail_label: str


class RankedDotsSpec(_ChartBase):
    kind: Literal["ranked_dots"] = "ranked_dots"
    series: tuple[RankedSeries, ...] = Field(min_length=1)


ChartSpec = Annotated[
    StintBarsSpec
    | PositionLinesSpec
    | RangedDotsSpec
    | GridTimelineSpec
    | RankedDotsSpec,
    Field(discriminator="kind"),
]

CHART_SPEC: TypeAdapter[ChartSpec] = TypeAdapter(ChartSpec)
