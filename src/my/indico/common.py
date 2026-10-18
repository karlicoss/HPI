"""
The model of what is kept of Indico sites: events, their agendas, and the files attached.
"""

from __future__ import annotations

from my.core import __NOT_HPI_MODULE__  # noqa: F401  # isort: skip

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Instance:
    """One Indico site, under the name the user gave it."""

    name: str  # 'fnal'
    url: str  # 'https://indico.fnal.gov'
    username: str | None  # the user's login there, if the user said


@dataclass(frozen=True)
class Person:
    name: str  # 'Viren, Brett'
    affiliation: str | None
    email_hash: str | None  # MD5 of the email address, which is all Indico shows
    mine: bool  # whether this is the user


@dataclass(frozen=True)
class Category:
    instance: str
    id: int
    title: str
    path: tuple[tuple[int, str], ...]  # (id, title) from the root, this one last

    @property
    def custom_key(self) -> str:
        return f'{self.instance}:{self.id}'


@dataclass(frozen=True)
class Attachment:
    """A file, or a link, attached to an event, a contribution or a sub-contribution."""

    instance: str
    id: int
    event: int
    contribution: int | None
    subcontribution: int | None
    folder: str | None  # 'Slides'
    title: str
    kind: str  # 'file' or 'link'
    filename: str | None
    content_type: str | None
    size: int | None
    checksum: str | None  # MD5, which Indico gives
    modified: datetime | None
    url: str | None  # where the site gives the file, or the link
    status: str | None  # what became of it when downloading was tried: 'ok', 'skipped: too big', 'error: ...'
    path: Path | None  # the file on this computer, if it was downloaded and is still there

    @property
    def downloaded(self) -> bool:
        return self.path is not None


@dataclass(frozen=True)
class SubContribution:
    instance: str
    event: int
    contribution: int
    id: int  # as in the site's URLs, which is unique on the site
    friendly_id: int | None  # the number in its contribution
    title: str
    description: str
    duration: int | None  # minutes
    speakers: tuple[Person, ...]
    attachments: tuple[Attachment, ...]


@dataclass(frozen=True)
class Contribution:
    """A talk, or a poster, or whatever an event's agenda is made of."""

    instance: str
    event: int
    id: int  # as in the site's URLs, which is unique on the site
    friendly_id: int | None  # the number in its event
    title: str
    description: str
    start: datetime | None
    end: datetime | None
    duration: int | None  # minutes
    session: str | None
    track: str | None
    type: str | None
    location: str | None
    room: str | None
    url: str | None
    speakers: tuple[Person, ...]
    authors: tuple[Person, ...]  # primary authors
    coauthors: tuple[Person, ...]
    attachments: tuple[Attachment, ...]
    subcontributions: tuple[SubContribution, ...]
    mine: bool  # whether the user speaks or is an author

    @property
    def all_attachments(self) -> tuple[Attachment, ...]:
        return self.attachments + tuple(a for s in self.subcontributions for a in s.attachments)


@dataclass(frozen=True)
class Session:
    instance: str
    event: int
    id: int
    title: str
    description: str
    start: datetime | None
    end: datetime | None
    location: str | None
    room: str | None
    conveners: tuple[Person, ...]
    mine: bool  # whether the user convenes it


@dataclass(frozen=True)
class Event:
    """An event as seen when it was last fetched, and its agenda as seen when that was last fetched."""

    instance: str
    id: int
    title: str
    description: str
    type: str | None  # 'meeting', 'lecture', 'conference'
    start: datetime | None
    end: datetime | None
    timezone: str | None
    location: str | None
    room: str | None
    address: str | None
    url: str
    category: Category
    keywords: tuple[str, ...]
    created: datetime | None
    creator: str | None
    chairs: tuple[Person, ...]
    attachments: tuple[Attachment, ...]  # those of the event itself
    sessions: tuple[Session, ...]
    contributions: tuple[Contribution, ...]
    has_agenda: bool  # whether any view fetched the agenda; if not, there are no sessions or contributions to show
    observed: datetime  # when the event itself was last fetched
    agenda_observed: datetime | None
    mine: bool  # whether the user chairs, convenes, speaks or is an author

    @property
    def key(self) -> str:
        return f'{self.instance}:{self.id}'
