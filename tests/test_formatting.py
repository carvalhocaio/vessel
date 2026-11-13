import pytest

from vessel.formatting import (
    compound_name,
    format_decimal,
    format_lap_time,
    slugify,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("São Paulo", "sao-paulo"),
        ("Mexico City", "mexico-city"),
        ("  Spa-Francorchamps! ", "spa-francorchamps"),
        ("Yas Marina (Abu Dhabi)", "yas-marina-abu-dhabi"),
    ],
)
def test_slugify(text: str, expected: str) -> None:
    assert slugify(text) == expected


@pytest.mark.parametrize(
    ("value", "places", "expected"),
    [
        (0.2, 1, "0,2"),
        (1.2345, 3, "1,234"),
        (1234.5, 1, "1.234,5"),
        (-0.05, 2, "-0,05"),
        (12, 0, "12"),
    ],
)
def test_format_decimal_uses_pt_br_separators(
    value: float, places: int, expected: str
) -> None:
    assert format_decimal(value, places) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(72.689, "1:12,689"), (59.9996, "1:00,000"), (9.5, "0:09,500")],
)
def test_format_lap_time(seconds: float, expected: str) -> None:
    assert format_lap_time(seconds) == expected


def test_compound_name_in_portuguese() -> None:
    assert compound_name("INTERMEDIATE") == "intermediário"
    assert compound_name("TEST_UNKNOWN") == "test_unknown"
