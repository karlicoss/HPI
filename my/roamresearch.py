"""
[[https://roamresearch.com][Roam]] data
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime, timezone
from itertools import chain
from pathlib import Path
from typing import NamedTuple

from my.config import roamresearch as config

from .core import Json, LazyLogger, get_files

logger = LazyLogger(__name__)


def last() -> Path:
    return max(get_files(config.export_path))


class Keys:
    CREATED    = 'create-time'
    EDITED     = 'edit-time'
    EDIT_EMAIL = 'edit-email'
    STRING     = 'string'
    CHILDREN   = 'children'
    TITLE      = 'title'
    UID        = 'uid'


class Node(NamedTuple):
    raw: Json

    # TODO not sure if UTC
    @property
    def created(self) -> datetime:
        ct = self.raw.get(Keys.CREATED)
        if ct is not None:
            return datetime.fromtimestamp(ct / 1000, tz=timezone.utc)
        # ugh. daily notes don't have create time for some reason???

        title = self.title
        if title is None:
            return self.edited # fallback TODO log?
        # the format is 'February 8th, 2020'. Fucking hell.
        m = re.fullmatch(r'(\w+) (\d+)\w+, (\d+)', title)
        if m is None:
            return self.edited # fallback TODO log?
        # strip off 'th'/'rd' crap
        dts = m.group(1) + ' ' + m.group(2) + ' ' + m.group(3)
        dt = datetime.strptime(dts, '%B %d %Y').replace(tzinfo=timezone.utc)
        return dt

    @property
    def edited(self) -> datetime:
        rt = self.raw[Keys.EDITED]
        return datetime.fromtimestamp(rt / 1000, tz=timezone.utc)

    @property
    def title(self) -> str | None:
        return self.raw.get(Keys.TITLE)

    @property
    def body(self) -> str | None:
        return self.raw.get(Keys.STRING)

    @property
    def children(self) -> list[Node]:
        # TODO cache? needs a key argument (because of Json)
        ch = self.raw.get(Keys.CHILDREN, [])
        return list(map(Node, ch))

    @property
    def path(self) -> str:
        username = config.username # sadly, Roam research export doesn't provide it
        return f'{username}/page/{self.uid}'

    @property
    def permalink(self) -> str:
        return f'https://roamresearch.com/#/app/{self.path}'

    @property
    def uid(self) -> str:
        u = self.raw.get(Keys.UID)
        if u is not None:
            return u
        # ugh. so None apparently means "Daily note"

        # yes, it is using US date format...
        return self.created.strftime('%m-%d-%Y')

    def empty(self) -> bool:
        # sometimes nodes are empty. two cases:
        # - no heading -- child notes, like accidental enter presses I guess
        # - heading    -- notes that haven't been created yet
        return len(self.body or '') == 0 and len(self.children) == 0

    def traverse(self) -> Iterator[Node]:
        # not sure about __iter__, because might be a bit unintuitive that it's recursive..
        yield self
        for c in self.children:
            yield from c.traverse()

    def _render(self) -> Iterator[str]:
        ss = f'[{self.created:%Y-%m-%d %H:%M}] {self.title or " "}'
        body = self.body
        sc = chain.from_iterable(c._render() for c in self.children)

        yield ss
        if body is not None:
            yield body
        yield self.permalink
        for c in sc:
            yield '|  ' + c

    def render(self) -> str:
        return '\n'.join(self._render())

    def __repr__(self):
        return f'Node(created={self.created}, title={self.title}, body={self.body})'

    @staticmethod
    def make(raw: Json) -> Iterator[Node]:
        is_empty = set(raw.keys()) == {Keys.EDITED, Keys.EDIT_EMAIL, Keys.TITLE}
        # not sure about that... but daily notes end up like that
        if is_empty:
            # todo log?
            return
        yield Node(raw)


class Roam:
    def __init__(self, raw: list[Json]) -> None:
        self.raw = raw

    @property
    def notes(self) -> list[Node]:
        return list(chain.from_iterable(map(Node.make, self.raw)))

    def traverse(self) -> Iterator[Node]:
        for n in self.notes:
            yield from n.traverse()


def roam() -> Roam:
    import json
    raw = json.loads(last().read_text())
    roam = Roam(raw)
    return roam


def print_all_notes():
    # just a demo method
    # TODO demonstrate dumping as org-mode??
    for n in roam().notes:
        print(n.render())

# TODO could generate org-mode mirror in a single file for a demo?
