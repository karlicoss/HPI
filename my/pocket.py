"""
[[https://getpocket.com][Pocket]] bookmarks and highlights
"""
from dataclasses import dataclass
from typing import Optional

from .core import Paths, PathIsh

from my.config import pocket as user_config


@dataclass
class pocket(user_config):
    '''
    Uses [[https://github.com/karlicoss/pockexport][pockexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths

    # path to a local clone of pockexport
    # alternatively, you can put the repository (or a symlink) in $MY_CONFIG/my/config/repos/pockexport
    pockexport  : Optional[PathIsh] = None

    @property
    def dal_module(self):
        rpath = self.pockexport
        if rpath is not None:
            from .core.common import import_dir
            return import_dir(rpath, '.dal')
        else:
            import my.config.repos.pockexport.dal as dal
            return dal


from .core.cfg import make_config
config = make_config(pocket)


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import my.config.repos.pockexport.dal as dal
else:
    dal = config.dal_module

############################

Article = dal.Article

from pathlib import Path
from typing import Sequence, Iterable


# todo not sure if should be defensive against empty?
def _dal() -> dal.DAL:
    from .core import get_files
    inputs = get_files(config.export_path)
    return dal.DAL(inputs)


def articles() -> Iterable[Article]:
    yield from _dal().articles()


def stats():
    from itertools import chain
    from more_itertools import ilen
    # todo make stats more defensive?
    return {
        'articles'  : ilen(articles()),
        'highlights': ilen(chain.from_iterable(a.highlights for a in articles())),
    }


# todo deprecate?
def get_articles() -> Sequence[Article]:
    return list(articles())
