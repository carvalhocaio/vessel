from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from tests.factories import FIXTURES, regulation_document
from vessel.cache import FileCache
from vessel.domain import Section
from vessel.sources.fia_source import (
    INDEX_URL,
    FiaRegulationSource,
    documents_from_index,
    pdf_key,
)

INDEX = (FIXTURES / "fia_regulations_index.html").read_bytes()


class FakeHttp:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        return INDEX if url == INDEX_URL else b"%PDF-fake"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 13, 12, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def test_index_lists_section_documents_from_titles() -> None:
    documents = documents_from_index(INDEX.decode("utf-8"))

    assert [doc.label for doc in documents] == [
        "2026 A Iss 03",
        "2026 C Iss 20",
        "2026 C Iss 21",
        "2027 B Iss 01",
    ]
    technical = documents[2]
    assert technical.section is Section.TECHNICAL
    assert technical.published_on == date(2026, 10, 19)
    assert str(technical.url).endswith("section_c_technical_-_iss_21_-_2026-10-19.pdf")


def test_relative_links_are_resolved_against_fia() -> None:
    general = documents_from_index(INDEX.decode("utf-8"))[0]

    assert str(general.url).startswith("https://www.fia.com/")


def test_archive_and_legacy_documents_are_skipped() -> None:
    labels = {doc.label for doc in documents_from_index(INDEX.decode("utf-8"))}

    assert not any(label.startswith("2025") for label in labels)
    assert len(labels) == 4


def test_index_is_cached_for_twelve_hours(tmp_path: Path) -> None:
    http, clock = FakeHttp(), Clock()
    source = FiaRegulationSource(FileCache(tmp_path, clock), http)

    source.documents()
    clock.now += timedelta(hours=11)
    source.documents()
    clock.now += timedelta(hours=2)
    source.documents()

    assert http.calls == [INDEX_URL, INDEX_URL]


def test_pdf_is_downloaded_once_and_kept_forever(tmp_path: Path) -> None:
    http, clock = FakeHttp(), Clock()
    source = FiaRegulationSource(FileCache(tmp_path, clock), http)
    document = regulation_document(21)

    assert not source.has_pdf(document)
    source.pdf(document)
    clock.now += timedelta(days=400)
    source.pdf(document)

    assert http.calls == [str(document.url)]
    assert source.has_pdf(document)
    assert pdf_key(document).startswith("regulations/pdf/fia_2026_f1_regulations")
