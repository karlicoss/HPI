'''
Programmatic access and queries to org-mode files on the filesystem
'''

REQUIRES = [
    'orgparse',
]

from datetime import datetime
from pathlib import Path
import re
from typing import List, Sequence, Iterable, NamedTuple, Optional, Tuple

from my.core import get_files
from my.core.common import mcachew
from my.core.cachew import cache_dir
from my.core.orgmode import collect

from my.config import orgmode as user_config

import orgparse


# temporary? hack to cache org-mode notes
class OrgNote(NamedTuple):
    created: Optional[datetime]
    heading: str
    tags: List[str]


def inputs() -> Sequence[Path]:
    return get_files(user_config.paths)


_rgx = re.compile(orgparse.date.gene_timestamp_regex(brtype='inactive'), re.VERBOSE)
def _created(n: orgparse.OrgNode) -> Tuple[Optional[datetime], str]:
    heading = n.heading
    # meh.. support in orgparse?
    pp = {} if n.is_root() else n.properties # type: ignore
    createds = pp.get('CREATED', None)
    if createds is None:
        # try to guess from heading
        m = _rgx.search(heading)
        if m is not None:
            createds = m.group(0) # could be None
    if createds is None:
        return (None, heading)
    assert isinstance(createds, str)
    [odt] = orgparse.date.OrgDate.list_from_str(createds)
    dt = odt.start
    # todo a bit hacky..
    heading = heading.replace(createds + ' ', '')
    return (dt, heading)


def to_note(x: orgparse.OrgNode) -> OrgNote:
    # ugh. hack to merely make it cacheable
    heading = x.heading
    created: Optional[datetime]
    try:
        c, heading = _created(x)
        if isinstance(c, datetime):
            created = c
        else:
            # meh. not sure if should return date...
            created = None
    except Exception as e:
        created = None
    return OrgNote(
        created=created,
        heading=heading, # todo include the body?
        tags=list(x.tags),
    )


# todo move to common?
def _sanitize(p: Path) -> str:
    return re.sub(r'\W', '_', str(p))


class Query:
    def __init__(self, files: Sequence[Path]) -> None:
        self.files = files

    # TODO yield errors?
    @mcachew(
        cache_path=lambda _, f: cache_dir() / 'orgmode' / _sanitize(f), force_file=True,
        depends_on=lambda _, f: (f, f.stat().st_mtime),
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


from my.core import Stats, stat
def stats() -> Stats:
    def outlines():
        return query().all()
    return stat(outlines)
