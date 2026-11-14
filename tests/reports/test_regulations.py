import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.factories import StaticTables, regulation_articles
from vessel.analytics.registry import CalcInputs
from vessel.domain import Draft, RegulationScope, Section, Segment, Source
from vessel.reports.drafts import DraftVerificationError
from vessel.reports.regulations import (
    build_regulations,
    export_chunks,
    regulations_dir,
)
from vessel.verify import verifier

NOW = datetime(2026, 11, 13, 17, tzinfo=UTC)
SCOPE = RegulationScope(
    season=2026, section=Section.TECHNICAL, from_issue=20, to_issue=21
)


def served(old_issue_frame: object | None = None) -> StaticTables:
    old = regulation_articles(20) if old_issue_frame is None else old_issue_frame
    return StaticTables(
        CalcInputs(
            regulation_tables={
                (2026, "technical", 20): old,  # type: ignore[dict-item]
                (2026, "technical", 21): regulation_articles(21),
            }
        )
    )


def test_regulations_draft_lists_changes_with_citations(tmp_path: Path) -> None:
    directory = regulations_dir(tmp_path, SCOPE)

    draft = build_regulations(
        SCOPE,
        regulation_articles(20),
        regulation_articles(21),
        directory,
        now=NOW,
        verify=verifier(served()),
    )

    assert directory == tmp_path / "2026" / "regulations" / "technical" / "20-21"
    saved = Draft.model_validate(
        json.loads((directory / "draft.json").read_text("utf-8"))
    )
    assert saved == draft
    assert saved.segment is Segment.REGULATIONS
    assert saved.regulation == SCOPE
    assert saved.event is None
    assert saved.charts == ()
    assert saved.sources == (Source.FIA,)
    facts = {fact.key: fact for fact in saved.facts}
    assert facts["articles_added"].value == 0
    chapter = facts["chapter_c5_changes"]
    assert "Art. C5.2.12" in chapter.context
    assert "Iss 21" in chapter.context
    assert "iss_21.pdf" in chapter.context
    assert chapter.provenance.calculation == "regulations.chapter_changes"
    assert chapter.provenance.params["chapter"] == "C5"
    assert [ref.kind for ref in chapter.provenance.inputs] == [
        "regulation",
        "regulation",
    ]


def test_divergent_regulation_draft_is_rejected(tmp_path: Path) -> None:
    tampered = regulation_articles(20)
    tampered.loc[tampered["number"] == "C1.1", "text"] = "Texto adulterado."
    directory = regulations_dir(tmp_path, SCOPE)

    with pytest.raises(DraftVerificationError, match="articles_changed"):
        build_regulations(
            SCOPE,
            regulation_articles(20),
            regulation_articles(21),
            directory,
            now=NOW,
            verify=verifier(served(tampered)),
        )

    assert not (directory / "draft.json").exists()


def test_chunks_are_one_json_line_per_article(tmp_path: Path) -> None:
    path = tmp_path / "chunks.jsonl"

    count = export_chunks(regulation_articles(21), path)

    lines = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
    assert count == len(lines) == 9
    first = lines[1]
    assert first["id"] == "2026-technical-iss21-C1.1"
    assert first["text"].startswith("C1.1 Amendments to these Technical Regulations\n")
    assert first["metadata"]["parent"] == "C1"
    assert first["metadata"]["page_start"] == 7
    assert first["metadata"]["url"].endswith("iss_21.pdf")
