'''
Stackexchange data
'''
REQUIRES = [
    'git+https://github.com/karlicoss/stexport',
]

# TODO use GDPR?

from stexport import dal
from my.config import stackexchange as config


# todo lru cache?
def _dal() -> dal.DAL:
    from ..core import get_files
    inputs = get_files(config.export_path)
    return dal.DAL(inputs)


def site(name: str) -> dal.SiteDAL:
    return _dal().site_dal(name)


from ..core import stat, Stats
def stats() -> Stats:
    s = site('stackoverflow')
    return stat(s.questions)
