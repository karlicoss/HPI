'''
Programmatic access and queries to org-mode files on the filesystem
'''

from __future__ import annotations

REQUIRES = [
    'orgparse',
]

import re
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional

import orgparse

from my.core import Paths, Stats, get_files, stat
from my.core.cachew import cache_dir, mcachew
from my.core.orgmode import collect


class config:
    paths: Paths


def make_config() -> config:
    from my.config import orgmode as user_config

    class combined_config(user_config, config): ...

    return combined_config()


# temporary? hack to cache org-mode notes
class OrgNote(NamedTuple):
    created: Optional[datetime]
    heading: str
    tags: list[str]


def inputs() -> Sequence[Path]:
    cfg = make_config()
    return get_files(cfg.paths)


_rgx = re.compile(orgparse.date.gene_timestamp_regex(brtype='inactive'), re.VERBOSE)


def _created(n: orgparse.OrgNode) -> tuple[datetime | None, str]:
    heading = n.heading
    # meh.. support in orgparse?
    pp = {} if n.is_root() else n.properties
    createds = pp.get('CREATED', None)
    if createds is None:
        # try to guess from heading
        m = _rgx.search(heading)
        if m is not None:
            createds = m.group(0)  # could be None
    if createds is None:
        return (None, heading)
    assert isinstance(createds, str), createds  # in orgparse it could be float/int etc
    [odt] = orgparse.date.OrgDate.list_from_str(createds)
    dt = odt.start
    if not isinstance(dt, datetime):
        # could be date | datetime
        return (None, heading)
    heading = heading.replace(createds + ' ', '')
    return (dt, heading)


def to_note(x: orgparse.OrgNode) -> OrgNote:
    # ugh. hack to merely make it cacheable
    heading = x.heading
    created: datetime | None
    try:
        c, heading = _created(x)
        if isinstance(c, datetime):
            created = c
        else:
            # meh. not sure if should return date...
            created = None
    except Exception:
        created = None
    return OrgNote(
        created=created,
        heading=heading,  # todo include the body?
        tags=list(x.tags),
    )


# todo move to common?
def _sanitize(p: Path) -> str:
    return re.sub(r'\W', '_', str(p))


def _cachew_cache_path(_self, f: Path) -> Path:
    return cache_dir() / 'orgmode' / _sanitize(f)


def _cachew_depends_on(_self, f: Path):
    return (f, f.stat().st_mtime)


class Query:
    def __init__(self, files: Sequence[Path]) -> None:
        self.files = files

    # TODO yield errors?
    @mcachew(
        cache_path=_cachew_cache_path,
        force_file=True,
        depends_on=_cachew_depends_on,
    )
    def _iterate(self, f: Path) -> Iterable[OrgNote]:
        o = orgparse.load(f)
        for x in o:
            yield to_note(x)

    def all(self) -> Iterable[OrgNote]:
        # TODO  build a virtual hierarchy from it?
        for f in self.files:
            yield from self._iterate(f)

    def collect_all(self, collector) -> Iterable[orgparse.OrgNode]:
        for f in self.files:
            o = orgparse.load(f)
            yield from collect(o, collector)


def query() -> Query:
    return Query(files=inputs())


def stats() -> Stats:
    def outlines():
        return query().all()

    return stat(outlines)
