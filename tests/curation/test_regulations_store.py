from pathlib import Path

import pandas as pd
import pytest

from tests.factories import FakeRegulationSource, parsed_fixture, regulation_document
from vessel.cache import FileCache
from vessel.curation.regulations import (
    CuratedRegulationStore,
    MissingRegulationError,
    latest_issues,
)
from vessel.domain import RegulationDocument, Section


def make_store(
    tmp_path: Path, *issues: int
) -> tuple[CuratedRegulationStore, FakeRegulationSource]:
    documents = tuple(
        regulation_document(issue).model_copy(update={"sha256": None})
        for issue in issues
    )
    source = FakeRegulationSource(documents)
    store = CuratedRegulationStore(FileCache(tmp_path), source, parse=parsed_fixture)
    return store, source


def test_sync_curates_the_last_two_issues(tmp_path: Path) -> None:
    store, source = make_store(tmp_path, 19, 20, 21)

    results = store.sync()

    assert [result.document.issue for result in results] == [20, 21]
    assert source.downloads == [20, 21]
    assert (tmp_path / "regulations/2026/technical/21/articles.parquet").is_file()
    articles = store.articles(2026, Section.TECHNICAL, 21)
    assert "C5.2.12" in set(articles["number"])
    assert articles["sha256"].iloc[0] is not None
    assert str(articles["document_url"].iloc[0]).endswith("iss_21.pdf")


def test_published_issue_is_never_downloaded_again(tmp_path: Path) -> None:
    store, source = make_store(tmp_path, 20, 21)
    store.sync()

    second = store.sync()

    assert source.downloads == [20, 21]
    assert not any(result.downloaded for result in second)


def test_documents_are_remembered_with_their_sha(tmp_path: Path) -> None:
    store, _ = make_store(tmp_path, 20, 21)
    store.sync()

    documents = store.documents()

    assert [doc.issue for doc in documents] == [20, 21]
    assert all(doc.sha256 and len(doc.sha256) == 64 for doc in documents)


def test_every_issue_with_all_flag(tmp_path: Path) -> None:
    store, source = make_store(tmp_path, 20, 21)

    store.sync(every_issue=True)

    assert source.downloads == [20, 21]


def test_missing_issue_names_the_command(tmp_path: Path) -> None:
    store, _ = make_store(tmp_path, 21)

    with pytest.raises(MissingRegulationError, match="vessel regs sync --all"):
        store.articles(2026, Section.TECHNICAL, 5)


def test_latest_issues_per_season_and_section() -> None:
    documents = tuple(regulation_document(issue) for issue in (18, 19, 20, 21))

    assert [doc.issue for doc in latest_issues(documents)] == [20, 21]


def test_same_pdf_under_another_url_reuses_articles(tmp_path: Path) -> None:
    store, source = make_store(tmp_path, 20, 21)
    store.sync()
    calls: list[int] = []

    def counting_parse(pdf: bytes, section: Section) -> pd.DataFrame:
        calls.append(1)
        return parsed_fixture(pdf, section)

    reupload = regulation_document(21).model_copy(
        update={
            "sha256": None,
            "issue": 22,
            "url": "https://www.fia.com/system/files/documents/reupload_0.pdf",
        }
    )
    twin = CuratedRegulationStore(
        FileCache(tmp_path),
        FakeTwinSource(source, reupload),
        parse=counting_parse,
    )

    twin.sync()

    assert calls == []
    reused = twin.articles(2026, Section.TECHNICAL, 22)
    assert int(reused["issue"].iloc[0]) == 22
    assert str(reused["document_url"].iloc[0]).endswith("reupload_0.pdf")


class FakeTwinSource:
    def __init__(
        self, base: FakeRegulationSource, reupload: RegulationDocument
    ) -> None:
        self._base = base
        self._reupload = reupload

    def documents(self) -> tuple[RegulationDocument, ...]:
        return (*self._base.documents(), self._reupload)

    def pdf(self, document: RegulationDocument) -> bytes:
        issue = 21 if document == self._reupload else document.issue
        return f"pdf-{issue}".encode()

    def has_pdf(self, document: RegulationDocument) -> bool:
        return document != self._reupload


def test_reparse_rebuilds_articles_from_cached_pdfs(tmp_path: Path) -> None:
    store, source = make_store(tmp_path, 20, 21)
    store.sync()
    calls: list[int] = []

    def counting_parse(pdf: bytes, section: Section) -> pd.DataFrame:
        calls.append(1)
        return parsed_fixture(pdf, section)

    again = CuratedRegulationStore(FileCache(tmp_path), source, parse=counting_parse)
    again.sync()
    again.sync(reparse=True)

    assert len(calls) == 2
