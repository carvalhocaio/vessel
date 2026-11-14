import pandas as pd

from tests.factories import regulation_articles
from vessel.regulations.diff import chapter_of, diff_issues, ligature_variant


def articles(**texts: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "number": number.replace("_", "."),
                "title": None,
                "text": text,
                "notes": "",
                "page_start": 1,
            }
            for number, text in texts.items()
        ]
    )


def test_added_removed_and_changed_articles() -> None:
    old = articles(C1_1="Power is 350kW.", C1_2="Gone soon.", C1_3="Same text.")
    new = articles(C1_1="Power is 400kW.", C1_3="Same text.", C1_4="Brand new.")

    diff = diff_issues(old, new)

    assert diff.added == ("C1.4",)
    assert diff.removed == ("C1.2",)
    [changed] = diff.changed
    assert changed.number == "C1.1"
    assert changed.chapter == "C1"
    assert changed.before == "Power is 350kW."
    assert changed.after == "Power is 400kW."
    assert 0 < changed.similarity < 1


def test_whitespace_and_line_breaks_are_ignored() -> None:
    old = articles(C1_1="The car must\n be  rigid.", C1_2="a. first b.second")
    new = articles(C1_1="The car must be rigid.", C1_2="a. first b. second")

    assert diff_issues(old, new).changed == ()


def test_broken_ligatures_are_not_changes() -> None:
    old = articles(C1_1="installation diaerences between oa-board chargers")
    new = articles(C1_1="installation differences between off-board chargers")

    assert diff_issues(old, new).changed == ()
    assert ligature_variant("Diiuser", "Diffuser")
    assert not ligature_variant("power", "tower")


def test_snippet_shows_repaired_words_around_the_edit() -> None:
    old = articles(C1_1="the diaerent cells defined in C5 are allowed")
    new = articles(C1_1="the different cells defined in Appendix C1 are allowed")

    [changed] = diff_issues(old, new).changed

    assert changed.before == "the different cells defined in C5 are allowed"
    assert "Appendix C1" in changed.after


def test_real_issues_detect_the_mgu_k_change() -> None:
    diff = diff_issues(regulation_articles(20), regulation_articles(21))

    numbers = {article.number for article in diff.changed}
    assert "C5.2.12" in numbers
    assert "C1.1" not in numbers
    assert diff.added == ()


def test_chapter_of_handles_appendices() -> None:
    assert chapter_of("C3.10.2") == "C3"
    assert chapter_of("CAPP2") == "CAPP2"
