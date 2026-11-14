import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from vessel.domain import Article, Section

BOLD_FLAG = 16
WHITE = 0xFFFFFF
CHANGE_COLORS = frozenset({0xFF00FF, 0xFF40FF})
NOTE_COLORS = frozenset({0xC00000, 0xFF9900, 0x00B050})
TOP_BAND = 0.09
BOTTOM_BAND = 0.92
REPEATED_SHARE = 0.5
MIN_TOC_ENTRIES = 5
SAME_LINE_TOLERANCE = 2.0
_HYPHENS = str.maketrans(dict.fromkeys("\u2010\u2011\u2012\u2212", "-"))
APPENDIX_INFIX = "APP"
SOFT_HYPHEN = "\u00ad"

_BOILERPLATE = (
    re.compile(r"^©\s*\d{4}\s+Fédération Internationale de l.Automobile$"),
    re.compile(r"^Issue \d+$"),
    re.compile(r"^\d{1,2} [A-Z][a-z]+ \d{4}$"),
    re.compile(r"^\d{4} Formula 1 Regulations - Section [A-F] \[.+\]$"),
    re.compile(r"^SECTION [A-F]: [A-Z ]+REGULATIONS$"),
)
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")
_LIST_MARKER = re.compile(r"^(?:[a-z]|[ivx]+)\.\s")


@dataclass(frozen=True, slots=True)
class Line:
    page: int
    y: float
    text: str
    bold: bool = False
    color: int = 0
    changed: bool = False
    height: float = 842.0

    @property
    def position(self) -> float:
        return self.y / self.height


@dataclass(slots=True)
class _Draft:
    number: str
    title: str | None
    page_start: int
    page_end: int
    parts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    changed: bool = False


Pages = list[list[Line]]


def pdf_lines(pdf: bytes) -> Pages:
    import pymupdf  # noqa: PLC0415

    pages: Pages = []
    with pymupdf.open(stream=pdf, filetype="pdf") as document:  # type: ignore[no-untyped-call]
        for number, page in enumerate(document, start=1):
            pages.append(_page_lines(number, page.get_text("dict"), page.rect.height))
    return pages


def strip_repeated(pages: Pages) -> Pages:
    in_band = Counter(
        key
        for page in pages
        for key in {_band_key(line) for line in page if _in_band(line)}
    )
    threshold = max(2, int(len(pages) * REPEATED_SHARE))
    repeated = {key for key, count in in_band.items() if count >= threshold}
    return [
        [
            line
            for line in page
            if line.color != WHITE
            and not (_in_band(line) and _band_key(line) in repeated)
            and not any(pattern.match(line.text) for pattern in _BOILERPLATE)
        ]
        for page in pages
    ]


def join_lines(lines: Iterable[str]) -> str:
    text = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if not text:
            text = line
        elif text.endswith("-") and line[:1].islower():
            text += line
        elif _LIST_MARKER.match(line):
            text += "\n" + line
        else:
            text += " " + line
    return text


def parse_articles(pages: Pages, section: Section) -> list[Article]:
    letter = section.letter
    heading = re.compile(rf"^(?:ARTICLE\s+)?({letter}\d+(?:\.\d+)*)(?::|\s|$)\s*(.*)$")
    appendix = re.compile(rf"^APPENDIX\s+{letter}(\d+)(?::|\s|$)\s*(.*)$")
    toc_heading = re.compile(
        rf"^(?:ARTICLE|APPENDIX)\s+{letter}\d+(?:\.\d+)*:?\s.+\s\d+$"
    )
    toc_entry = re.compile(
        rf"^(?:ARTICLE\s+|APPENDIX\s+)?{letter}\d+(?:\.\d+)*:?\s.+\s\d+$"
    )
    drafts: dict[str, _Draft] = {}
    current: _Draft | None = None
    for page in strip_repeated(pages):
        if sum(1 for line in page if toc_entry.match(line.text)) >= MIN_TOC_ENTRIES:
            continue
        for line in page:
            if line.bold and toc_heading.match(line.text):
                continue
            found = _heading(line, heading, appendix, letter)
            if found:
                number, title = found
                current = drafts.get(number) or _Draft(
                    number, title, line.page, line.page
                )
                drafts.setdefault(number, current)
                current.changed |= line.changed
                continue
            if current is None:
                continue
            current.page_end = line.page
            current.changed |= line.changed
            if line.color in NOTE_COLORS:
                current.notes.append(line.text)
            else:
                current.parts.append(line.text)
    numbers = set(drafts)
    return [
        Article(
            number=draft.number,
            title=draft.title,
            text=join_lines(draft.parts),
            page_start=draft.page_start,
            page_end=draft.page_end,
            parent=_parent(draft.number, numbers),
            marked_changed=draft.changed,
            notes=join_lines(draft.notes),
        )
        for draft in drafts.values()
    ]


def _heading(
    line: Line, heading: re.Pattern[str], appendix: re.Pattern[str], letter: str
) -> tuple[str, str | None] | None:
    if not line.bold:
        return None
    if match := appendix.match(line.text):
        return f"{letter}{APPENDIX_INFIX}{match.group(1)}", match.group(
            2
        ).strip() or None
    if match := heading.match(line.text):
        return match.group(1), match.group(2).strip() or None
    return None


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).replace(SOFT_HYPHEN, "")
    return _SPACES.sub(" ", folded.translate(_HYPHENS)).strip()


def _parent(number: str, numbers: set[str]) -> str | None:
    parts = number.split(".")
    while len(parts) > 1:
        parts.pop()
        candidate = ".".join(parts)
        if candidate in numbers:
            return candidate
    return None


def _in_band(line: Line) -> bool:
    return line.position < TOP_BAND or line.position > BOTTOM_BAND


def _band_key(line: Line) -> str:
    return _DIGITS.sub("#", line.text)


def _page_lines(number: int, page: Any, height: float) -> list[Line]:
    rows: list[tuple[float, list[tuple[float, list[Any]]]]] = []
    for block in page.get("blocks", []):
        for raw in block.get("lines", []):
            spans = [span for span in raw["spans"] if str(span["text"]).strip()]
            if not spans:
                continue
            y, x = float(raw["bbox"][3]), float(raw["bbox"][0])
            row = next((r for r in rows if abs(r[0] - y) <= SAME_LINE_TOLERANCE), None)
            if row is None:
                rows.append((y, [(x, spans)]))
            else:
                row[1].append((x, spans))
    return [_line(number, y, pieces, height) for y, pieces in sorted(rows)]


def _line(
    number: int, y: float, pieces: list[tuple[float, list[Any]]], height: float
) -> Line:
    ordered = [spans for _, spans in sorted(pieces, key=lambda piece: piece[0])]
    spans = [span for piece in ordered for span in piece]
    weights = Counter[int]()
    for span in spans:
        weights[int(span["color"])] += len(str(span["text"]))
    return Line(
        page=number,
        y=round(y, 1),
        text=normalize(
            " ".join("".join(str(s["text"]) for s in piece) for piece in ordered)
        ),
        bold=bool(int(spans[0]["flags"]) & BOLD_FLAG),
        color=weights.most_common(1)[0][0],
        changed=any(int(span["color"]) in CHANGE_COLORS for span in spans),
        height=round(height, 1),
    )
