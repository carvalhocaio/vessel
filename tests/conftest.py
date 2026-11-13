import pytest

from tests.factories import make_sao_paulo
from vessel.domain import Event


@pytest.fixture
def sao_paulo() -> Event:
    return make_sao_paulo()
