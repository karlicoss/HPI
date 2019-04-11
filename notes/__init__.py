from glob import glob
from typing import List, Sequence
from pathlib import Path

from kython.ktyping import PathIsh

from porg import Org # type: ignore


# TODO enc stuff?
def get_org_paths():
    return [
        '***REMOVED***',
        '***REMOVED***',
    ]

def _get_org_files_in(path, archived: bool=False) -> List[PathIsh]:
    ppp = Path(path)
    assert ppp.exists()
    # TODO try/catch??
    if ppp.is_file():
        return [ppp]

    path = str(path) # TODO FIXME use pathlib
    res = []
    res.extend(glob(path + '/**/*.org', recursive=True))
    if archived:
        res.extend(glob(path + '/**/*.org_archive', recursive=True))
    return res


def get_org_files(archived: bool = False) -> List[PathIsh]:
    res = []
    for p in get_org_paths():
        res.extend(_get_org_files_in(p, archived=archived))
    return res


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
            for of in _get_org_files_in(p):
                org = Org.from_file(of)
                res.extend(query(org))
        return res


def get_notes():
    return PorgAll(get_org_paths())
