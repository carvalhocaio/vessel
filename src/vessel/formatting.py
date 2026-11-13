import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_PT_BR_SEPARATORS = str.maketrans({",": ".", ".": ","})


def slugify(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    )
    return _NON_ALNUM.sub("-", ascii_text.lower()).strip("-")


def format_decimal(value: float, places: int = 1) -> str:
    return f"{value:,.{places}f}".translate(_PT_BR_SEPARATORS)
