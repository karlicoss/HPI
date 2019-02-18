from glob import glob
from typing import List

from porg import Org # typing: ignore

# TODO enc stuff?
def get_org_paths():
    return [
        '***REMOVED***',
        '***REMOVED***',
    ]

def _get_org_files_in(path, archived: bool=False) -> List[str]:
    res = []
    res.extend(glob(path + '/**/*.org', recursive=True))
    if archived:
        res.extend(glob(path + '/**/*.org_archive', recursive=True))
    return res


def get_org_files(archived: bool = False) -> List[str]:
    res = []
    for p in get_org_paths():
        res.extend(_get_org_files_in(p, archived=archived))
    return res


# TODO move to porg?
class PorgAll:
    def __init__(self, paths: List[str]) -> None:
        self.paths = paths

    def get_all(self):
        return self.query_all(lambda x: x.xpath_all('//*'))

    def query_all(self, query):
        res = []
        for p in self.paths:
            for of in _get_org_files_in(p):
                org = Org.from_file(of)
                res.extend(query(org))
        return res


def get_notes():
    return PorgAll(get_org_paths())
