import pytest

from tests.factories import (
    load_race_2026_20,
    load_schedule_2026,
    load_session_tables,
    make_sao_paulo,
    make_singapore,
)
from vessel.curation import RaceTables, SessionTables
from vessel.domain import Event


@pytest.fixture
def sao_paulo() -> Event:
    return make_sao_paulo()


@pytest.fixture
def schedule_2026() -> tuple[Event, ...]:
    return load_schedule_2026()


@pytest.fixture
def race_2026_20() -> RaceTables:
    return load_race_2026_20()


@pytest.fixture
def singapore() -> Event:
    return make_singapore()


@pytest.fixture
def fp2_2026_20() -> SessionTables:
    return load_session_tables("fp2_2026_20")


@pytest.fixture
def sprint_2026_17() -> SessionTables:
    return load_session_tables("sprint_2026_17")
