import logging
import re
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import httpx

from vessel.cache import FileCache, Forever, Ttl
from vessel.domain import RegulationDocument, Section
from vessel.sources.calendar_source import HttpGet

logger = logging.getLogger(__name__)

INDEX_URL = "https://www.fia.com/regulation/category/110"
INDEX_KEY = "regulations/index.html"
INDEX_MAX_AGE = timedelta(hours=12)
USER_AGENT = "vessel (+https://github.com/carvalhocaio/vessel)"
TIMEOUT_S = 60.0

_TITLE = re.compile(
    r"^FIA (?P<season>\d{4}) F1 Regulations - Section (?P<letter>[A-F]) \[.+?\]"
    r" - Iss (?P<issue>\d+) - (?P<date>\d{4}-\d{2}-\d{2})$"
)
_KEY_UNSAFE = re.compile(r"[^a-z0-9_.-]+")


def http_get(url: str) -> bytes:
    response = httpx.get(
        url,
        timeout=TIMEOUT_S,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.content


class FiaRegulationSource:
    def __init__(self, cache: FileCache, get: HttpGet = http_get) -> None:
        self._cache = cache
        self._get = get

    def documents(self) -> tuple[RegulationDocument, ...]:
        html = self._cache.fetch(
            INDEX_KEY, Ttl(INDEX_MAX_AGE), lambda: self._get(INDEX_URL)
        )
        return documents_from_index(html.decode("utf-8"))

    def pdf(self, document: RegulationDocument) -> bytes:
        return self._cache.fetch(
            pdf_key(document), Forever(), lambda: self._get(str(document.url))
        )

    def has_pdf(self, document: RegulationDocument) -> bool:
        return self._cache.read(pdf_key(document)) is not None


def pdf_key(document: RegulationDocument) -> str:
    name = PurePosixPath(urlparse(str(document.url)).path).name.lower()
    return f"regulations/pdf/{_KEY_UNSAFE.sub('_', name)}"


def documents_from_index(html: str) -> tuple[RegulationDocument, ...]:
    parser = _IndexParser()
    parser.feed(html)
    documents: dict[tuple[int, Section, int], RegulationDocument] = {}
    for url, title in parser.items:
        match = _TITLE.match(" ".join(title.split()))
        if match is None:
            logger.debug("skipping regulation outside the section format: %s", title)
            continue
        document = RegulationDocument(
            season=int(match["season"]),
            section=Section.from_letter(match["letter"]),
            issue=int(match["issue"]),
            published_on=date.fromisoformat(match["date"]),
            url=urljoin(INDEX_URL, url),
        )
        documents.setdefault(
            (document.season, document.section, document.issue), document
        )
    return tuple(
        sorted(documents.values(), key=lambda d: (d.season, d.section.letter, d.issue))
    )


class _IndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, str]] = []
        self._href: str | None = None
        self._in_title = False
        self._title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and (values.get("href") or "").endswith(".pdf"):
            self._href = values["href"]
            self._title = []
        elif tag == "div" and self._href and values.get("class") == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._in_title:
            self._in_title = False
        elif tag == "a" and self._href:
            self.items.append((self._href, "".join(self._title)))
            self._href = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title.append(data)
