from glob import glob
from typing import List

from porg import Org # typing: ignore

# TODO move to porg?
class PorgAll:
    def __init__(self, paths: List[str]) -> None:
        self.paths = paths

    def query_all(self, query):
        res = []
        for p in self.paths:
            ofiles = glob(p + '/**/*.org', recursive=True)
            for of in ofiles:
                org = Org.from_file(of)
                res.extend(query(org))
        return res


def get_notes():
    ORG_PATHS = [
        '***REMOVED***',
        '***REMOVED***',
    ]
    return PorgAll(ORG_PATHS)
