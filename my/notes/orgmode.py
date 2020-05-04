'''
Programmatic access and queries to org-mode files on the filesystem
'''

from glob import glob
from typing import List, Sequence, Iterator
from pathlib import Path

from ..common import PathIsh

from my.config import orgmode as config

from porg import Org


# TODO not sure about symlinks?
def _org_files_in(ppp: Path, archived: bool=False) -> Iterator[Path]:
    assert ppp.exists(), ppp
    # TODO reuse get_files somehow?
    if ppp.is_file():
        return [ppp]

    yield from ppp.rglob('*.org')
    if archived:
        yield from ppp.rglob('*.org_archive')


def org_files(roots=config.roots, archived: bool=False) -> Iterator[Path]:
    # TODO rename to 'paths'? use get_files?
    for p in config.roots:
        yield from _org_files_in(Path(p), archived=archived)


# TODO move to porg?
class PorgAll:
    # TODO *roots?
    def __init__(self, roots: Sequence[PathIsh]) -> None:
        self.files = org_files(roots=roots)

    def xpath_all(self, query: str):
        return self.query_all(lambda x: x.xpath_all(query))

    def get_all(self):
        return self.xpath_all('/')

    def query_all(self, query):
        res: List[Org] = []
        for of in self.files:
            org = Org.from_file(str(of))
            res.extend(query(org))
        return res


def query():
    return PorgAll(roots=config.roots)
