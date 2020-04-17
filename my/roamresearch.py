"""
[[Roam][https://roamresearch.com]] data
"""
from datetime import datetime
from pathlib import Path
from itertools import chain
from typing import NamedTuple, Iterator, List, Optional

import pytz

from .common import get_files, LazyLogger, Json

from my.config import roamresearch as config

logger = LazyLogger(__name__)


def last() -> Path:
    return max(get_files(config.export_path, '*.json'))


class Keys:
    CREATED    = 'create-time'
    EDITED     = 'edit-time'
    EDIT_EMAIL = 'edit-email'
    STRING     = 'string'
    CHILDREN   = 'children'
    TITLE      = 'title'


class Node(NamedTuple):
    raw: Json

    # TODO not sure if UTC
    @property
    def created(self) -> datetime:
        ct = self.raw.get(Keys.CREATED)
        if ct is None:
            # e.g. daily notes don't have create time for some reason???
            return self.edited
        else:
            return datetime.fromtimestamp(ct / 1000, tz=pytz.utc)

    @property
    def edited(self) -> datetime:
        rt = self.raw[Keys.EDITED]
        return datetime.fromtimestamp(rt / 1000, tz=pytz.utc)

    @property
    def title(self) -> Optional[str]:
        return self.raw.get(Keys.TITLE)

    @property
    def body(self) -> Optional[str]:
        return self.raw.get(Keys.STRING)

    @property
    def children(self) -> List['Node']:
        ch = self.raw.get(Keys.CHILDREN, [])
        return list(map(Node, ch))

    def _render(self) -> Iterator[str]:
        ss = f'[{self.created:%Y-%m-%d %H:%M}] {self.title or " "}'
        body = self.body
        sc = chain.from_iterable(c._render() for c in self.children)

        yield ss
        if body is not None:
            yield body
        for c in sc:
            yield '|  ' + c

    def render(self) -> str:
        return '\n'.join(self._render())

    def __repr__(self):
        return f'Node(created={self.created}, title={self.title}, body={self.body})'

    @staticmethod
    def make(raw: Json) -> Iterator['Node']:
        is_empty = set(raw.keys()) == {Keys.EDITED, Keys.EDIT_EMAIL, Keys.TITLE}
        # not sure about that... but daily notes end up like that
        if is_empty:
            # todo log?
            return
        yield Node(raw)


class Roam:
    def __init__(self, json: List[Json]) -> None:
        self.nodes: List[Node] = []
        # TODO make it lazy?
        for j in json:
            self.nodes.extend(Node.make(j))


def roam() -> Roam:
    import json
    raw = json.loads(last().read_text())
    roam = Roam(raw)
    return roam


def print_all_notes():
    # just a demo method
    # TODO demonstrate dumping as org-mode??
    for n in roam().nodes:
        print(n.render())

# TODO could generate org-mode mirror in a single file for a demo?
