'''
Programmatic access and queries to org-mode files on the filesystem
'''
from datetime import datetime
from pathlib import Path
from typing import List, Sequence, Iterable, NamedTuple, Optional

from .core import PathIsh
from .core.common import mcachew
from .core.cachew import cache_dir

from my.config import orgmode as user_config


from porg import Org


# temporary? hack to cache org-mode notes
class OrgNote(NamedTuple):
    created: Optional[datetime]
    heading: str
    tags: List[str]


# todo move to common?
import re
def _sanitize(p: Path) -> str:
    return re.sub(r'\W', '_', str(p))


# todo move to porg?
class Query:
    def __init__(self, files: Sequence[Path]) -> None:
        self.files = files

    # TODO yield errors?
    @mcachew(
        cache_path=lambda _, f: cache_dir() / 'orgmode' / _sanitize(f), force_file=True,
        depends_on=lambda _, f: (f, f.stat().st_mtime),
    )
    def _iterate(self, f: Path) -> Iterable[OrgNote]:
        o = Org.from_file(f)
        for x in o.iterate():
            try:
                # TODO(porg) not sure if created should ever throw... maybe warning/log?
                created = x.created
            except Exception as e:
                created = None
            yield OrgNote(
                created=created,
                heading=x.heading, # todo include the rest?
                tags=list(x.tags),
            )

    def all(self) -> Iterable[OrgNote]:
        for f in self.files:
            yield from self._iterate(f)

    # TODO very confusing names...
    # TODO careful... maybe use orgparse iterate instead?? ugh.
    def get_all(self):
        return self._xpath_all('//org')

    def query_all(self, query):
        for of in self.files:
            org = Org.from_file(str(of))
            yield from query(org)

    def _xpath_all(self, query: str):
        return self.query_all(lambda x: x.xpath_all(query))


def query() -> Query:
    return Query(files=list(user_config.files))
