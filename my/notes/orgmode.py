from glob import glob
from typing import List, Sequence, Iterator
from pathlib import Path

from ..common import PathIsh

from mycfg import orgmode as config

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


def org_files(archived: bool=False) -> Iterator[Path]:
    for p in config.roots:
        yield from _org_files_in(Path(p), archived=archived)


# TODO move to porg?
class PorgAll:
    def __init__(self, paths: Sequence[PathIsh]) -> None:
        self.paths = [Path(p) for p in paths]

    def xpath_all(self, query: str):
        return self.query_all(lambda x: x.xpath_all(query))

    def get_all(self):
        return self.xpath_all('//*')

    def query_all(self, query):
        res: List[Org] = []
        for p in self.paths:
            for of in _org_files_in(p):
                org = Org.from_file(str(of))
                res.extend(query(org))
        return res


def notes():
    return PorgAll(org_files())
