import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_PT_BR_SEPARATORS = str.maketrans({",": ".", ".": ","})
_SECONDS_PER_MINUTE = 60

COMPOUND_NAMES = {
    "SOFT": "macio",
    "MEDIUM": "médio",
    "HARD": "duro",
    "INTERMEDIATE": "intermediário",
    "WET": "chuva",
}


def slugify(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    return _NON_ALNUM.sub("-", ascii_text.lower()).strip("-")


def format_decimal(value: float, places: int = 1) -> str:
    return f"{value:,.{places}f}".translate(_PT_BR_SEPARATORS)


def format_lap_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    minutes, rest = divmod(milliseconds, _SECONDS_PER_MINUTE * 1000)
    return f"{minutes}:{format_decimal(rest / 1000, 3).zfill(6)}"


def compound_name(compound: str) -> str:
    return COMPOUND_NAMES.get(compound.upper(), compound.lower())
