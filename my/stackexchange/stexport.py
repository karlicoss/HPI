'''
Stackexchange data (uses API via [[https://github.com/karlicoss/stexport][stexport]])
'''
REQUIRES = [
    'git+https://github.com/karlicoss/stexport',
]

### config
from my.config import stackexchange as user_config
from ..core import dataclass, PathIsh, make_config
@dataclass
class stackexchange(user_config):
    '''
    Uses [[https://github.com/karlicoss/stexport][stexport]] outputs
    '''
    export_path: PathIsh  # path to GDPR zip file
config = make_config(stackexchange)
###

from stexport import dal


# todo lru cache?
def _dal() -> dal.DAL:
    from ..core import get_files
    inputs = get_files(config.export_path)
    return dal.DAL(inputs)


# TODO not sure if should keep the sites separate.. probably easier to filter after than merge
def site(name: str) -> dal.SiteDAL:
    return _dal().site_dal(name)


from ..core import stat, Stats
def stats() -> Stats:
    s = site('stackoverflow')
    return stat(s.questions)
