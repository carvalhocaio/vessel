import json
from collections.abc import Hashable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from vessel.analytics.registry import CalcInputs, compute_facts
from vessel.analytics.regulations import (
    CHAPTER_FACT,
    REGULATION_FACTS,
    diff_from,
    regulation_params,
    top_chapters,
)
from vessel.domain import (
    Draft,
    RegulationScope,
    RegulationTableRef,
    Segment,
)
from vessel.reports.drafts import Verifier, publish_draft

CAVEATS = (
    "Comparação artigo a artigo pelo número: um artigo renumerado aparece como "
    "removido e incluído.",
    "Texto riscado pela FIA (excluído) pode aparecer junto do texto novo em "
    "referências renumeradas.",
    "Diferenças só de espaço, quebra de linha, ligaduras tipográficas e símbolos de "
    "tabela são ignoradas.",
    "Cada apêndice vira um item único (ex.: CAPP1); páginas de desenho que repetem o "
    "título de outro apêndice podem misturar conteúdo entre eles.",
    "Citar só trechos curtos e linkar o PDF oficial na fia.com; o documento não é "
    "redistribuído.",
)


def regulations_dir(out_dir: Path, scope: RegulationScope) -> Path:
    return (
        out_dir
        / str(scope.season)
        / Segment.REGULATIONS.value
        / scope.section.value
        / f"{scope.from_issue:02d}-{scope.to_issue:02d}"
    )


def regulation_refs(scope: RegulationScope) -> tuple[RegulationTableRef, ...]:
    return tuple(
        RegulationTableRef(season=scope.season, section=scope.section, issue=issue)
        for issue in (scope.from_issue, scope.to_issue)
    )


def build_regulations(
    scope: RegulationScope,
    old: pd.DataFrame,
    new: pd.DataFrame,
    directory: Path,
    *,
    now: datetime,
    verify: Verifier,
) -> Draft:
    key = (scope.season, scope.section.value)
    inputs = CalcInputs(
        regulation_tables={
            (*key, scope.from_issue): old,
            (*key, scope.to_issue): new,
        }
    )
    refs = regulation_refs(scope)
    params = regulation_params(scope)
    facts = compute_facts(REGULATION_FACTS, inputs, refs, params)
    for chapter in top_chapters(diff_from(inputs, params)):
        facts += compute_facts(
            (CHAPTER_FACT,), inputs, refs, params | {"chapter": chapter}
        )
    draft = Draft(
        segment=Segment.REGULATIONS,
        regulation=scope,
        facts=facts,
        caveats=CAVEATS,
        generated_at=now,
    )
    publish_draft(draft, directory, verify)
    return draft


def export_chunks(articles: pd.DataFrame, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = articles.sort_values("position").to_dict("records")
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(chunk(row), ensure_ascii=False) + "\n")
    return len(rows)


def chunk(row: Mapping[Hashable, Any]) -> dict[str, object]:
    number = str(row["number"])
    title = _clean(row["title"])
    issue = int(row["issue"])
    heading = f"{number} {title}" if title else number
    return {
        "id": f"{row['season']}-{row['section']}-iss{issue:02d}-{number}",
        "text": f"{heading}\n{row['text']}".strip(),
        "metadata": {
            "season": int(row["season"]),
            "section": str(row["section"]),
            "issue": issue,
            "number": number,
            "title": title,
            "parent": _clean(row["parent"]),
            "page_start": int(row["page_start"]),
            "page_end": int(row["page_end"]),
            "published_on": str(row["published_on"]),
            "url": str(row["document_url"]),
            "notes": _clean(row["notes"]) or None,
        },
    }


def _clean(value: Any) -> Any:
    return None if value is None or pd.isna(value) else value
