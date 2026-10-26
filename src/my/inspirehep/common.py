"""
The model of the data InspireHEP has about one author, shared by the sources that provide it.
"""

from __future__ import annotations

from my.core import __NOT_HPI_MODULE__  # noqa: F401  # isort: skip

from dataclasses import dataclass
from datetime import date, datetime

INSPIRE_URL = 'https://inspirehep.net'

# InspireHEP's ranks of a position that mean the person was studying rather than employed
EDUCATION_RANKS = frozenset({'PHD', 'MASTER', 'UNDERGRADUATE'})


@dataclass(frozen=True)
class Profile:
    """Who the author is."""

    recid: int
    name: str  # 'Viren, Brett Michael'
    preferred_name: str | None  # 'Brett Viren'
    status: str | None  # 'active', 'retired', 'deceased'...
    ids: dict[str, tuple[str, ...]]  # by schema, e.g. 'ORCID', 'INSPIRE BAI'
    emails: tuple[str, ...]
    urls: tuple[str, ...]
    arxiv_categories: tuple[str, ...]
    native_names: tuple[str, ...]
    created: datetime | None
    updated: datetime | None

    @property
    def url(self) -> str:
        return f'{INSPIRE_URL}/authors/{self.recid}'


@dataclass(frozen=True)
class Position:
    """Where the author worked or studied."""

    institution: str  # 'Brookhaven'
    institution_id: int | None
    location: str | None  # 'Upton, NY, United States'
    rank: str | None  # InspireHEP's: 'SENIOR', 'POSTDOC', 'PHD'...
    start: str | None  # as given, which may be only a year: '1993', '1993-05'
    end: str | None
    start_date: date | None  # best effort, a missing month or day taken as the first
    end_date: date | None
    current: bool

    @property
    def is_education(self) -> bool:
        return self.rank in EDUCATION_RANKS


@dataclass(frozen=True)
class Advisor:
    name: str
    recid: int | None
    degree_type: str | None  # 'phd', 'other'...
    ids: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class Experiment:
    """An experiment, or a collaboration, that InspireHEP knows."""

    recid: int
    name: str  # the legacy name, e.g. 'FNAL-E-0974'
    long_name: str | None
    collaboration: str | None  # e.g. 'MicroBooNE'
    description: str | None
    urls: tuple[str, ...]
    started: str | None
    completed: str | None
    papers: int | None  # all papers InspireHEP has for it

    @property
    def url(self) -> str:
        return f'{INSPIRE_URL}/experiments/{self.recid}'


@dataclass(frozen=True)
class Membership:
    """The author's relation to an experiment, as the profile declares it."""

    name: str
    recid: int | None
    current: bool
    experiment: Experiment | None  # when the dump has its record


@dataclass(frozen=True)
class Collaboration:
    """
    A collaboration or experiment the author is part of, from their profile, from their papers, or both.
    """

    name: str  # 'MicroBooNE'
    recid: int | None
    papers: int  # of the author's, signed with it; 0 if the profile is the only evidence
    first: date | None  # date of the earliest of those papers
    last: date | None
    current: bool | None  # per the profile; None if the profile does not say
    experiment: Experiment | None
    membership: Membership | None  # the profile's entry, whose name may differ: 'FNAL-E-0974'
    paper_ids: tuple[int, ...] = ()  # record numbers of those papers, newest first


@dataclass(frozen=True)
class Paper:
    recid: int
    title: str
    abstract: str | None
    date: date | None  # InspireHEP's earliest date, a missing month or day taken as the first
    date_text: str | None  # as given: '2022', '2022-03', '2022-03-18'
    document_types: tuple[str, ...]  # 'article', 'conference paper', 'thesis'...
    arxiv_id: str | None
    arxiv_category: str | None
    dois: tuple[str, ...]
    journal: str | None  # 'JINST 17 (2022) P11022'
    conference: str | None  # the cnum, 'C22-10-24.1'
    published: bool  # refereed
    citations: int
    citations_without_self: int
    collaborations: tuple[str, ...]
    experiments: tuple[str, ...]
    first_author: str | None
    author_count: int
    keywords: tuple[str, ...]
    categories: tuple[str, ...]  # InspireHEP's subject areas
    texkey: str | None
    report_numbers: tuple[str, ...]
    pages: int | None
    urls: tuple[str, ...]

    @property
    def url(self) -> str:
        return f'{INSPIRE_URL}/literature/{self.recid}'

    @property
    def arxiv_url(self) -> str | None:
        return None if self.arxiv_id is None else f'https://arxiv.org/abs/{self.arxiv_id}'

    @property
    def doi_url(self) -> str | None:
        return f'https://doi.org/{self.dois[0]}' if self.dois else None


@dataclass(frozen=True)
class Seminar:
    recid: int
    title: str
    start: datetime | None  # UTC, as InspireHEP stores it
    end: datetime | None
    timezone: str | None  # where it was held
    venue: str | None
    series: tuple[str, ...]
    abstract: str | None
    urls: tuple[str, ...]
    categories: tuple[str, ...]

    @property
    def url(self) -> str:
        return f'{INSPIRE_URL}/seminars/{self.recid}'


@dataclass(frozen=True)
class Student:
    """Someone who names the author as their advisor."""

    recid: int
    name: str
    degree_type: str | None
    institution: str | None  # where they studied, when their profile says
    start: str | None
    end: str | None
    ids: dict[str, tuple[str, ...]]

    @property
    def url(self) -> str:
        return f'{INSPIRE_URL}/authors/{self.recid}'


@dataclass(frozen=True)
class CitationSummary:
    """InspireHEP's counts over the author's papers."""

    papers: int  # citeable papers
    published_papers: int
    citations: int
    published_citations: int
    h_index: int
    published_h_index: int
    average_citations: float | None
    # papers by number of citations: '0--0', '1--9', ... '500--'
    buckets: dict[str, int]
