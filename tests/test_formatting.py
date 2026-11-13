import pytest

from vessel.formatting import format_decimal, slugify


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
