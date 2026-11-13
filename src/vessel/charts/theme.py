from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    surface: str
    text_primary: str
    text_secondary: str
    muted: str
    grid: str
    baseline: str
    categorical: tuple[str, ...]


DARK = Theme(
    surface="#1a1a19",
    text_primary="#f0efec",
    text_secondary="#c3c2b7",
    muted="#898781",
    grid="#2c2c2a",
    baseline="#383835",
    categorical=(
        "#3987e5",
        "#d95926",
        "#199e70",
        "#c98500",
        "#d55181",
        "#008300",
        "#9085e9",
        "#e66767",
    ),
)

LIGHT = Theme(
    surface="#fcfcfb",
    text_primary="#0b0b0b",
    text_secondary="#52514e",
    muted="#898781",
    grid="#e1e0d9",
    baseline="#c3c2b7",
    categorical=(
        "#2a78d6",
        "#eb6834",
        "#1baf7a",
        "#eda100",
        "#e87ba4",
        "#008300",
        "#6250d6",
        "#e34948",
    ),
)
