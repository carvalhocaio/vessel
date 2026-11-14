import re
from collections.abc import Hashable, Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from vessel.regulations.parser import normalize

SNIPPET_CONTEXT_WORDS = 10
SNIPPET_LIMIT = 160
_CHAPTER = re.compile(r"^([A-F](?:APP)?\d+)")
LIGATURE = "ff"

Row = Mapping[Hashable, Any]
_TABLE_SYMBOLS = str.maketrans(dict.fromkeys("\u00fc\u00fb\u2713\u2714\u2717\u2718"))


@dataclass(frozen=True, slots=True)
class ChangedArticle:
    number: str
    title: str | None
    chapter: str
    similarity: float
    before: str
    after: str
    page_start: int


@dataclass(frozen=True, slots=True)
class RegulationDiff:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[ChangedArticle, ...]

    def changed_in(self, chapter: str) -> tuple[ChangedArticle, ...]:
        return tuple(article for article in self.changed if article.chapter == chapter)

    @property
    def chapters(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for article in self.changed:
            counts[article.chapter] = counts.get(article.chapter, 0) + 1
        return counts


def comparable(text: str) -> list[str]:
    return normalize(text).split()


def canonical(words: list[str]) -> list[str]:
    keys = (word.translate(_TABLE_SYMBOLS) for word in words)
    return [key for key in keys if key]


def ligature_variant(old: str, new: str) -> bool:
    for broken, intact in ((old, new), (new, old)):
        start = intact.find(LIGATURE)
        while start != -1:
            if (
                len(broken) == len(intact) - 1
                and broken[:start] == intact[:start]
                and broken[start + 1 :] == intact[start + len(LIGATURE) :]
            ):
                return True
            start = intact.find(LIGATURE, start + 1)
    return False


def chapter_of(number: str) -> str:
    match = _CHAPTER.match(number)
    return match.group(1) if match else number


def diff_issues(old: pd.DataFrame, new: pd.DataFrame) -> RegulationDiff:
    before = _by_number(old)
    after = _by_number(new)
    changed = []
    for number, row in after.items():
        previous = before.get(number)
        if previous is None:
            continue
        old_words = comparable(_content(previous))
        new_words = comparable(_content(row))
        old_keys, new_keys = canonical(old_words), canonical(new_words)
        if "".join(old_keys) == "".join(new_keys):
            continue
        matcher = SequenceMatcher(None, old_keys, new_keys, autojunk=False)
        edits = _real_edits(matcher, old_keys, new_keys)
        if not edits:
            continue
        repaired = _repaired(matcher, old_keys, new_keys)
        snippet_old, snippet_new = _snippets(edits[0], repaired, new_keys)
        changed.append(
            ChangedArticle(
                number=number,
                title=_title(row),
                chapter=chapter_of(number),
                similarity=round(matcher.ratio(), 4),
                before=snippet_old,
                after=snippet_new,
                page_start=int(str(row["page_start"])),
            )
        )
    return RegulationDiff(
        added=tuple(number for number in after if number not in before),
        removed=tuple(number for number in before if number not in after),
        changed=tuple(changed),
    )


def _content(row: Row) -> str:
    return f"{_title(row) or ''} {row['text']} {row.get('notes') or ''}"


def _title(row: Row) -> str | None:
    title = row["title"]
    return None if title is None or pd.isna(title) else str(title)


def _by_number(articles: pd.DataFrame) -> dict[str, Row]:
    return {str(row["number"]): row for row in articles.to_dict("records")}


Opcode = tuple[str, int, int, int, int]


def _real_edits(
    matcher: SequenceMatcher[str], old: list[str], new: list[str]
) -> list[Opcode]:
    return [
        op
        for op in matcher.get_opcodes()
        if op[0] != "equal" and not _only_ligatures(op, old, new)
    ]


def _repaired(
    matcher: SequenceMatcher[str], old: list[str], new: list[str]
) -> list[str]:
    repaired = list(old)
    for op in matcher.get_opcodes():
        tag, i1, i2, j1, j2 = op
        if tag == "replace" and _only_ligatures(op, old, new) and i2 - i1 == j2 - j1:
            repaired[i1:i2] = new[j1:j2]
    return repaired


def _only_ligatures(op: Opcode, old: list[str], new: list[str]) -> bool:
    tag, i1, i2, j1, j2 = op
    if "".join(old[i1:i2]) == "".join(new[j1:j2]):
        return True
    if tag != "replace" or i2 - i1 != j2 - j1:
        return False
    return all(
        ligature_variant(a, b) for a, b in zip(old[i1:i2], new[j1:j2], strict=True)
    )


def _snippets(op: Opcode, old: list[str], new: list[str]) -> tuple[str, str]:
    _, i1, i2, j1, j2 = op
    return _window(old, i1, i2), _window(new, j1, j2)


def _window(words: list[str], start: int, end: int) -> str:
    left = max(0, start - SNIPPET_CONTEXT_WORDS)
    right = min(len(words), max(end, start) + SNIPPET_CONTEXT_WORDS)
    snippet = " ".join(words[left:right])
    if len(snippet) > SNIPPET_LIMIT:
        snippet = snippet[:SNIPPET_LIMIT].rsplit(" ", 1)[0]
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(words) else ""
    return f"{prefix}{snippet}{suffix}"
