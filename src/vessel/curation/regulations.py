import hashlib
import io
import logging
from collections.abc import Callable, Hashable, Mapping
from dataclasses import dataclass
from typing import Any

import pandas as pd

from vessel.cache import FileCache, Forever
from vessel.curation.schema import ARTICLE_DTYPES, DOCUMENT_DTYPES, conform
from vessel.domain import RegulationDocument, Section
from vessel.regulations.parser import parse_articles, pdf_lines
from vessel.sources.ports import RegulationSource

logger = logging.getLogger(__name__)

DOCUMENTS_KEY = "regulations/documents.parquet"
DEFAULT_ISSUES_PER_SECTION = 2

Parser = Callable[[bytes, Section], pd.DataFrame]


class MissingRegulationError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class SyncResult:
    document: RegulationDocument
    articles: int
    downloaded: bool


def articles_key(season: int, section: Section, issue: int) -> str:
    return f"regulations/{season}/{section.value}/{issue}/articles.parquet"


def parse_pdf(pdf: bytes, section: Section) -> pd.DataFrame:
    articles = parse_articles(pdf_lines(pdf), section)
    return pd.DataFrame([article.model_dump() for article in articles])


class CuratedRegulationStore:
    def __init__(
        self, cache: FileCache, source: RegulationSource, parse: Parser = parse_pdf
    ) -> None:
        self._cache = cache
        self._source = source
        self._parse = parse

    def sync(
        self, *, every_issue: bool = False, reparse: bool = False
    ) -> list[SyncResult]:
        documents = self._source.documents()
        chosen = documents if every_issue else latest_issues(documents)
        results: list[SyncResult] = []
        known = {doc.url: doc for doc in self.documents()}
        synced: list[RegulationDocument] = []
        for document in chosen:
            downloaded = not self._source.has_pdf(document)
            articles = self._articles(known.get(document.url, document), reparse)
            synced.append(_with_sha(document, articles))
            results.append(SyncResult(synced[-1], len(articles), downloaded))
        self._save_documents(list(known.values()), synced)
        return results

    def documents(self) -> tuple[RegulationDocument, ...]:
        entry = self._cache.read(DOCUMENTS_KEY)
        if entry is None:
            return ()
        frame = conform(pd.read_parquet(io.BytesIO(entry.data)), DOCUMENT_DTYPES)
        return tuple(_document(row) for row in frame.to_dict("records"))

    def articles(self, season: int, section: Section, issue: int) -> pd.DataFrame:
        entry = self._cache.read(articles_key(season, section, issue))
        if entry is None:
            raise MissingRegulationError(
                f"{season} {section.value} issue {issue} is not curated; "
                "run: uv run vessel regs sync --all"
            )
        return conform(pd.read_parquet(io.BytesIO(entry.data)), ARTICLE_DTYPES)

    def _articles(
        self, document: RegulationDocument, reparse: bool = False
    ) -> pd.DataFrame:
        key = articles_key(document.season, document.section, document.issue)
        cached = None if reparse else self._cache.get(key, Forever())
        if cached is not None:
            return conform(pd.read_parquet(io.BytesIO(cached)), ARTICLE_DTYPES)
        pdf = self._source.pdf(document)
        sha = hashlib.sha256(pdf).hexdigest()
        twin = None if reparse else self._twin(sha, document)
        parsed = twin if twin is not None else self._parse(pdf, document.section)
        articles = articles_frame(parsed, document.model_copy(update={"sha256": sha}))
        buffer = io.BytesIO()
        articles.to_parquet(buffer, index=False)
        self._cache.put(key, buffer.getvalue())
        logger.info("curated %s: %d articles", document.label, len(articles))
        return articles

    def _twin(self, sha: str, document: RegulationDocument) -> pd.DataFrame | None:
        for other in self.documents():
            if other.sha256 == sha and other.url != document.url:
                try:
                    return self.articles(other.season, other.section, other.issue)
                except MissingRegulationError:
                    return None
        return None

    def _save_documents(
        self,
        known: list[RegulationDocument],
        synced: list[RegulationDocument],
    ) -> None:
        merged = {doc.url: doc for doc in known} | {doc.url: doc for doc in synced}
        frame = pd.DataFrame(
            [
                {
                    "season": doc.season,
                    "section": doc.section.value,
                    "issue": doc.issue,
                    "published_on": doc.published_on.isoformat(),
                    "url": str(doc.url),
                    "sha256": doc.sha256,
                }
                for doc in merged.values()
            ]
        )
        buffer = io.BytesIO()
        conform(frame, DOCUMENT_DTYPES).to_parquet(buffer, index=False)
        self._cache.put(DOCUMENTS_KEY, buffer.getvalue())


def latest_issues(
    documents: tuple[RegulationDocument, ...],
    per_section: int = DEFAULT_ISSUES_PER_SECTION,
) -> tuple[RegulationDocument, ...]:
    groups: dict[tuple[int, Section], list[RegulationDocument]] = {}
    for document in documents:
        groups.setdefault((document.season, document.section), []).append(document)
    return tuple(
        document
        for group in groups.values()
        for document in sorted(group, key=lambda d: d.issue)[-per_section:]
    )


def articles_frame(parsed: pd.DataFrame, document: RegulationDocument) -> pd.DataFrame:
    frame = parsed.copy()
    frame["season"] = document.season
    frame["section"] = document.section.value
    frame["issue"] = document.issue
    frame["published_on"] = document.published_on.isoformat()
    frame["document_url"] = str(document.url)
    frame["sha256"] = document.sha256
    frame["position"] = range(len(frame))
    return conform(frame, ARTICLE_DTYPES)


def _with_sha(
    document: RegulationDocument, articles: pd.DataFrame
) -> RegulationDocument:
    sha = articles["sha256"].iloc[0] if not articles.empty else None
    return document.model_copy(update={"sha256": None if pd.isna(sha) else str(sha)})


def _document(row: Mapping[Hashable, Any]) -> RegulationDocument:
    sha = row["sha256"]
    return RegulationDocument.model_validate(
        {
            "season": row["season"],
            "section": row["section"],
            "issue": row["issue"],
            "published_on": row["published_on"],
            "url": row["url"],
            "sha256": None if pd.isna(sha) else sha,
        }
    )
