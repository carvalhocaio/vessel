import pymupdf

from tests.factories import load_regulation_pages
from vessel.domain import Article, Section
from vessel.regulations.parser import (
    join_lines,
    normalize,
    parse_articles,
    pdf_lines,
    strip_repeated,
)

Color = tuple[float, float, float]

BLACK: Color = (0, 0, 0)
PINK: Color = (1, 0, 1)
RED: Color = (192 / 255, 0, 0)


def synthetic_pdf() -> bytes:
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    bodies: list[list[tuple[str, str, Color]]] = [
        [
            ("ARTICLE C1: GENERAL PRINCIPLES", "hebo", BLACK),
            ("C1.1 Scope", "hebo", BLACK),
            ("Governance: F1 Commission", "helv", RED),
            ("These regulations apply to every Formula 1 car and its", "helv", BLACK),
            ("compon-", "helv", BLACK),
            ("ents at all times.", "helv", BLACK),
        ],
        [
            ("C1.2 Changes", "hebo", BLACK),
            ("The maximum power is 350kW.", "helv", PINK),
            ("a. during the race.", "helv", BLACK),
        ],
        [
            ("C2 BODYWORK", "hebo", BLACK),
            ("C2.1 Front Wing", "hebo", BLACK),
            ("The front wing must be rigid.", "helv", BLACK),
        ],
    ]
    for body in bodies:
        page = document.new_page(width=595, height=842)
        page.insert_text((40, 30), "SECTION C: TECHNICAL REGULATIONS", fontsize=9)
        page.insert_text((40, 820), "Issue 21", fontsize=9)
        page.insert_text(
            (300, 820), "©2026 Fédération Internationale de l'Automobile", fontsize=9
        )
        for row, (text, font, color) in enumerate(body):
            page.insert_text((40, 120 + 20 * row), text, fontname=font, color=color)
    data: bytes = document.tobytes()  # type: ignore[no-untyped-call]
    return data


def by_number(articles: list[Article]) -> dict[str, Article]:
    return {article.number: article for article in articles}


def test_synthetic_pdf_lines_carry_style_and_position() -> None:
    pages = pdf_lines(synthetic_pdf())

    assert len(pages) == 3
    heading = next(line for line in pages[0] if line.text.startswith("C1.1"))
    assert heading.bold
    pink = next(line for line in pages[1] if "350kW" in line.text)
    assert pink.changed


def test_synthetic_pdf_becomes_articles() -> None:
    articles = by_number(parse_articles(pdf_lines(synthetic_pdf()), Section.TECHNICAL))

    assert list(articles) == ["C1", "C1.1", "C1.2", "C2", "C2.1"]
    assert articles["C1"].title == "GENERAL PRINCIPLES"
    assert articles["C1.1"].parent == "C1"
    assert articles["C2.1"].parent == "C2"
    assert articles["C1.1"].text == (
        "These regulations apply to every Formula 1 car and its compon-ents at all "
        "times."
    )
    assert articles["C1.1"].notes == "Governance: F1 Commission"
    assert articles["C1.2"].marked_changed
    assert not articles["C1.1"].marked_changed
    assert articles["C1.2"].text == "The maximum power is 350kW.\na. during the race."
    assert (articles["C2"].page_start, articles["C2.1"].page_end) == (3, 3)


def test_headers_and_footers_are_removed() -> None:
    texts = [
        line.text
        for page in strip_repeated(pdf_lines(synthetic_pdf()))
        for line in page
    ]

    assert "SECTION C: TECHNICAL REGULATIONS" not in texts
    assert "Issue 21" not in texts
    assert not any(text.startswith("©2026") for text in texts)


def test_real_pages_skip_contents_and_split_articles() -> None:
    articles = by_number(parse_articles(load_regulation_pages(21), Section.TECHNICAL))

    assert list(articles)[:5] == ["C1", "C1.1", "C1.2", "C1.3", "C1.4"]
    assert articles["C1.1"].title == "Amendments to these Technical Regulations"
    assert articles["C1.1"].text.startswith("Any amendments to these Technical")
    assert "Advisory Committee" in articles["C1"].notes
    assert articles["C5.2.12"].marked_changed
    every_text = " ".join(article.text for article in articles.values())
    assert "Fédération Internationale" not in every_text
    assert "Issue 21" not in every_text


def test_normalize_folds_ligatures_and_hyphens() -> None:
    assert normalize("speciﬁcation  re\u2212numbering MGU\u2011K") == (
        "specification re-numbering MGU-K"
    )


def test_join_lines_keeps_hyphenated_words_and_list_items() -> None:
    assert join_lines(["long-", "term plan", "a. first", "b. second"]) == (
        "long-term plan\na. first\nb. second"
    )
