from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from vessel.domain import (
    ChartPreset,
    ChartRef,
    Draft,
    Event,
    Fact,
    Segment,
    Source,
)

GENERATED_AT = datetime(2026, 11, 6, 23, 10, tzinfo=UTC)


def _fact(key: str = "pace_gap_top2", source: Source = Source.FASTF1) -> Fact:
    return Fact(
        key=key,
        value=0.2,
        unit="s/volta",
        display="0,2 s",
        context="média de 12 voltas no pneu médio, TL2",
        source=source,
    )


def _draft(event: Event, *facts: Fact, charts: tuple[ChartRef, ...] = ()) -> Draft:
    return Draft(
        segment=Segment.LONG_RUN,
        event=event.ref,
        facts=facts or (_fact(),),
        charts=charts,
        generated_at=GENERATED_AT,
    )


def test_round_trips_through_json(sao_paulo: Event) -> None:
    draft = _draft(
        sao_paulo,
        charts=(
            ChartRef(
                path="charts/long_run_x.png",
                spec_path="charts/long_run.json",
                preset=ChartPreset.X,
                sources=(Source.FASTF1,),
            ),
        ),
    )

    assert Draft.model_validate_json(draft.model_dump_json()) == draft


def test_schema_version_is_pinned(sao_paulo: Event) -> None:
    assert _draft(sao_paulo).schema_version == 2


def test_sources_merge_facts_and_charts_in_stable_order(sao_paulo: Event) -> None:
    draft = _draft(
        sao_paulo,
        _fact("pole_to_win_rate", Source.JOLPICA),
        _fact("pace_gap_top2", Source.FASTF1),
        charts=(
            ChartRef(
                path="charts/a.png",
                spec_path="charts/a.json",
                preset=ChartPreset.X,
                sources=(Source.FIA,),
            ),
        ),
    )

    assert draft.sources == (Source.FASTF1, Source.JOLPICA, Source.FIA)


def test_rejects_duplicated_fact_keys(sao_paulo: Event) -> None:
    with pytest.raises(ValidationError, match="unique"):
        _draft(sao_paulo, _fact(), _fact())


def test_requires_at_least_one_fact(sao_paulo: Event) -> None:
    with pytest.raises(ValidationError):
        Draft(
            segment=Segment.RACE_RECAP,
            event=sao_paulo.ref,
            facts=(),
            generated_at=GENERATED_AT,
        )


def test_rejects_unknown_fields(sao_paulo: Event) -> None:
    payload = _draft(sao_paulo).model_dump(mode="json") | {"tweet": "oi"}

    with pytest.raises(ValidationError):
        Draft.model_validate(payload)


@pytest.mark.parametrize("key", ["PaceGap", "1st_gap", "pace-gap", ""])
def test_fact_key_is_snake_case(key: str) -> None:
    with pytest.raises(ValidationError):
        _fact(key)


@pytest.mark.parametrize(
    "path", ["/tmp/chart.png", "../chart.png", "charts/../../x.png", "charts"]
)
def test_chart_path_stays_inside_draft(path: str) -> None:
    with pytest.raises(ValidationError, match="relative file"):
        ChartRef(
            path=path,
            spec_path="charts/a.json",
            preset=ChartPreset.X,
            sources=(Source.FASTF1,),
        )


def test_chart_spec_path_must_stay_inside_the_draft() -> None:
    with pytest.raises(ValidationError):
        ChartRef(
            path="charts/a.png",
            spec_path="../a.json",
            preset=ChartPreset.X,
            sources=(Source.FASTF1,),
        )
