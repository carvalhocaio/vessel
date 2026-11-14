from vessel.analytics.registry import (
    CalcInputs,
    Finding,
    Params,
    calculation,
    int_param,
    str_param,
)
from vessel.domain import ParamValue, RegulationScope, Source
from vessel.regulations.diff import ChangedArticle, RegulationDiff, diff_issues

REGULATION_FACTS = (
    "regulations.changed_count",
    "regulations.added_count",
    "regulations.removed_count",
)
CHAPTER_FACT = "regulations.chapter_changes"
TOP_CHAPTERS = 3
ARTICLES_PER_CHAPTER = 3


def regulation_params(scope: RegulationScope) -> dict[str, ParamValue]:
    return {
        "season": scope.season,
        "section": scope.section.value,
        "from_issue": scope.from_issue,
        "to_issue": scope.to_issue,
    }


def diff_from(inputs: CalcInputs, params: Params) -> RegulationDiff:
    season, section = int_param(params, "season"), str_param(params, "section")
    return diff_issues(
        inputs.regulation(season, section, int_param(params, "from_issue")),
        inputs.regulation(season, section, int_param(params, "to_issue")),
    )


def document_url(inputs: CalcInputs, params: Params) -> str:
    articles = inputs.regulation(
        int_param(params, "season"),
        str_param(params, "section"),
        int_param(params, "to_issue"),
    )
    return str(articles["document_url"].iloc[0])


def top_chapters(diff: RegulationDiff, limit: int = TOP_CHAPTERS) -> list[str]:
    ranked = sorted(diff.chapters.items(), key=lambda item: (-item[1], item[0]))
    return [chapter for chapter, _ in ranked[:limit]]


@calculation("regulations.changed_count", Source.FIA)
def changed_count(inputs: CalcInputs, params: Params) -> Finding | None:
    diff = diff_from(inputs, params)
    count = len(diff.changed)
    most = sorted(diff.changed, key=lambda article: article.similarity)[:1]
    detail = f" O de maior mudança é o {_cite(most[0])}." if most else ""
    return Finding(
        key="articles_changed",
        value=count,
        unit="articles",
        display=_articles(count),
        context=f"{_articles(count)} com texto alterado {_span(params)}.{detail} "
        f"PDF: {document_url(inputs, params)}",
    )


@calculation("regulations.added_count", Source.FIA)
def added_count(inputs: CalcInputs, params: Params) -> Finding | None:
    numbers = diff_from(inputs, params).added
    return _listing("articles_added", "incluído", numbers, inputs, params)


@calculation("regulations.removed_count", Source.FIA)
def removed_count(inputs: CalcInputs, params: Params) -> Finding | None:
    numbers = diff_from(inputs, params).removed
    return _listing("articles_removed", "removido", numbers, inputs, params)


@calculation("regulations.chapter_changes", Source.FIA)
def chapter_changes(inputs: CalcInputs, params: Params) -> Finding | None:
    chapter = str_param(params, "chapter")
    changed = diff_from(inputs, params).changed_in(chapter)
    if not changed:
        return None
    relevant = sorted(changed, key=lambda article: article.similarity)
    cited = "; ".join(_cite(article) for article in relevant[:ARTICLES_PER_CHAPTER])
    return Finding(
        key=f"chapter_{chapter.lower()}_changes",
        value=len(changed),
        unit="articles",
        display=f"{_articles(len(changed))} no {chapter}",
        context=f"No capítulo {chapter}, {_articles(len(changed))} "
        f"{'mudou' if len(changed) == 1 else 'mudaram'} "
        f"{_span(params)}. Mais relevantes: {cited}. "
        f"PDF: {document_url(inputs, params)}",
    )


def _listing(
    key: str,
    verb: str,
    numbers: tuple[str, ...],
    inputs: CalcInputs,
    params: Params,
) -> Finding:
    listed = f": {', '.join(numbers[:10])}" if numbers else ""
    return Finding(
        key=key,
        value=len(numbers),
        unit="articles",
        display=_articles(len(numbers)),
        context=f"{_articles(len(numbers))} {_plural(verb, len(numbers))} "
        f"{_span(params)}{listed}. "
        f"PDF: {document_url(inputs, params)}",
    )


def _cite(article: ChangedArticle) -> str:
    title = f" ({article.title[:60]})" if article.title else ""
    return (
        f"Art. {article.number}{title}, p. {article.page_start}, "
        f"similaridade {round(article.similarity * 100)}%: "
        f"antes «{article.before}», depois «{article.after}»"
    )


def _span(params: Params) -> str:
    return (
        f"da Iss {int_param(params, 'from_issue'):02d} para a "
        f"Iss {int_param(params, 'to_issue'):02d}"
    )


def _plural(word: str, count: int) -> str:
    return word if count == 1 else f"{word}s"


def _articles(count: int) -> str:
    return f"{count} artigo" if count == 1 else f"{count} artigos"
