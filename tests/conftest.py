import pytest

from tests.factories import load_schedule_2026, make_sao_paulo
from vessel.domain import Event


@pytest.fixture
def sao_paulo() -> Event:
    return make_sao_paulo()


@pytest.fixture
def schedule_2026() -> tuple[Event, ...]:
    return load_schedule_2026()
