import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_PT_BR_SEPARATORS = str.maketrans({",": ".", ".": ","})
_SECONDS_PER_MINUTE = 60

SESSION_LABELS = {
    "fp1": "TL1",
    "fp2": "TL2",
    "fp3": "TL3",
    "sprint_qualifying": "Classificação Sprint",
    "sprint": "Sprint",
    "qualifying": "Classificação",
    "race": "Corrida",
}

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


def format_lap_time(seconds: float, places: int = 3) -> str:
    scale = 10**places
    ticks = round(seconds * scale)
    minutes, rest = divmod(ticks, _SECONDS_PER_MINUTE * scale)
    width = 3 + places if places else 2
    return f"{minutes}:{format_decimal(rest / scale, places).zfill(width)}"


def format_signed(value: float, places: int = 1) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{format_decimal(abs(value), places)}"


def compound_name(compound: str) -> str:
    return COMPOUND_NAMES.get(compound.upper(), compound.lower())


def session_label(kind: str) -> str:
    return SESSION_LABELS[kind]


def session_phrase(kind: str) -> str:
    article = "no" if kind.startswith("fp") else "na"
    return f"{article} {session_label(kind)}"
