from datetime import date

import pandas as pd
import pytest

from tests.factories import facts_for
from vessel.analytics.form import (
    CHAMPIONSHIP_FACTS,
    DECIDED,
    FORM_FACTS,
    NO,
    YES,
    championship_math,
    championship_params,
    current_grid,
    form_params,
    recent_form,
)
from vessel.analytics.registry import CalcInputs
from vessel.curation import STANDING_DTYPES, SeasonTables, conform
from vessel.domain import Event, EventNotice, EventStatus


def by_round(events: tuple[Event, ...], round_: int) -> Event:
    return next(event for event in events if event.round == round_)


def with_status(
    events: tuple[Event, ...], status: EventStatus, *rounds: int
) -> tuple[Event, ...]:
    notice = EventNotice(status=status, note="nota", updated_on=date(2026, 11, 13))
    return tuple(
        event.with_notice(notice) if event.round in rounds else event
        for event in events
    )


def standings(leader: float, runner_up: float) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "driver": ["AAA", "BBB", "CCC"],
            "name": ["Alfa", "Bravo", "Charlie"],
            "nationality": ["Brazilian", "Dutch", "British"],
            "team": ["A", "B", "C"],
            "position": [1, 2, 3],
            "points": [leader, runner_up, runner_up - 10],
            "wins": [5, 3, 1],
        }
    )
    return conform(frame, STANDING_DTYPES)


def test_current_grid_comes_from_last_race(season_2026: SeasonTables) -> None:
    grid = current_grid(season_2026.results)

    assert len(grid) == 22
    assert {"ANT", "VER", "BOR", "CAM"} <= grid


def test_recent_form_uses_last_five_races(season_2026: SeasonTables) -> None:
    form = recent_form(season_2026.results).set_index("driver")

    assert form.loc["VER", "races"] == 5
    assert form.loc["VER", "avg_finish"] == pytest.approx(1.6)
    assert form.loc["VER", "podium_streak"] == 8
    assert form.loc["HAD", "points_streak"] == 13
    assert form.loc["BOT", "dnfs"] == 4


def test_form_facts(season_2026: SeasonTables) -> None:
    facts = {
        **facts_for(FORM_FACTS, CalcInputs(season_tables=season_2026), form_params())
    }

    assert facts["form_best_average"].display == "média 1,6"
    assert facts["form_podium_streak"].value == 8
    assert facts["form_points_streak"].value == 13
    assert facts["form_most_dnfs"].value == 4


def test_title_already_decided_before_las_vegas(
    season_2026: SeasonTables, schedule_2026: tuple[Event, ...]
) -> None:
    events = with_status(schedule_2026, EventStatus.AT_RISK, 22, 23)

    math = championship_math(
        season_2026.standings, championship_params(events, by_round(events, 21))
    )

    assert math is not None
    assert math.gap == 111
    assert math.available == 75
    assert math.rounds == (21, 22, 23)
    assert math.at_risk == (22, 23)
    assert math.verdict == DECIDED


def test_cancelled_rounds_do_not_count(schedule_2026: tuple[Event, ...]) -> None:
    events = with_status(schedule_2026, EventStatus.CANCELLED, 22)

    math = championship_math(
        standings(300, 260), championship_params(events, by_round(events, 21))
    )

    assert math is not None
    assert math.available == 50
    assert math.rounds == (21, 23)


def test_title_can_be_decided_here(schedule_2026: tuple[Event, ...]) -> None:
    math = championship_math(
        standings(300, 270),
        championship_params(schedule_2026, by_round(schedule_2026, 21)),
    )

    assert math is not None
    assert math.verdict == YES
    assert math.available_after == 50


def test_title_cannot_be_decided_here(schedule_2026: tuple[Event, ...]) -> None:
    math = championship_math(
        standings(300, 280),
        championship_params(schedule_2026, by_round(schedule_2026, 21)),
    )

    assert math is not None
    assert math.verdict == NO


def test_sprint_weekend_adds_sprint_points(schedule_2026: tuple[Event, ...]) -> None:
    singapore = by_round(schedule_2026, 17)

    math = championship_math(
        standings(300, 100), championship_params(schedule_2026, singapore)
    )

    assert math is not None
    assert math.at_stake_here == 33
    assert math.available == 33 + 6 * 25


def test_championship_facts(
    season_2026: SeasonTables, schedule_2026: tuple[Event, ...]
) -> None:
    params = championship_params(schedule_2026, by_round(schedule_2026, 21))

    facts = facts_for(CHAMPIONSHIP_FACTS, CalcInputs(season_tables=season_2026), params)

    assert facts["championship_gap"].display == "111 pontos"
    assert facts["championship_points_available"].value == 75
    assert facts["championship_can_be_decided"].value == DECIDED
    assert "Antonelli" in facts["championship_can_be_decided"].context
