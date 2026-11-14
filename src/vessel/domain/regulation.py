from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class Section(StrEnum):
    GENERAL = "general"
    SPORTING = "sporting"
    TECHNICAL = "technical"
    FINANCIAL_TEAMS = "financial_teams"
    FINANCIAL_PU = "financial_pu"
    OPERATIONAL = "operational"

    @property
    def letter(self) -> str:
        return SECTION_LETTERS[self]

    @property
    def official_name(self) -> str:
        return SECTION_NAMES[self]

    @classmethod
    def from_letter(cls, letter: str) -> "Section":
        return next(
            section for section, code in SECTION_LETTERS.items() if code == letter
        )


SECTION_LETTERS = {
    Section.GENERAL: "A",
    Section.SPORTING: "B",
    Section.TECHNICAL: "C",
    Section.FINANCIAL_TEAMS: "D",
    Section.FINANCIAL_PU: "E",
    Section.OPERATIONAL: "F",
}

SECTION_NAMES = {
    Section.GENERAL: "General Regulatory Provisions",
    Section.SPORTING: "Sporting",
    Section.TECHNICAL: "Technical",
    Section.FINANCIAL_TEAMS: "Financial - F1 Teams",
    Section.FINANCIAL_PU: "Financial - PU Manufacturers",
    Section.OPERATIONAL: "Operational",
}


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RegulationDocument(_Frozen):
    season: int = Field(ge=2026)
    section: Section
    issue: int = Field(ge=1)
    published_on: date
    url: HttpUrl
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @property
    def label(self) -> str:
        return f"{self.season} {self.section.letter} Iss {self.issue:02d}"


class Article(_Frozen):
    number: str = Field(pattern=r"^[A-F](?:APP)?\d+(\.\d+)*$")
    title: str | None = None
    text: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    parent: str | None = None
    marked_changed: bool = False
    notes: str = ""

    @model_validator(mode="after")
    def _pages_in_order(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("an article must end on or after its first page")
        return self


class RegulationScope(_Frozen):
    season: int = Field(ge=2026)
    section: Section
    from_issue: int = Field(ge=1)
    to_issue: int = Field(ge=1)

    @model_validator(mode="after")
    def _issues_in_order(self) -> Self:
        if self.to_issue <= self.from_issue:
            raise ValueError("to_issue must come after from_issue")
        return self
