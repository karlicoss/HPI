"""
[[https://getpocket.com][Pocket]] bookmarks and highlights
"""
REQUIRES = [
    'git+https://github.com/karlicoss/pockexport',
]
from dataclasses import dataclass
from typing import TYPE_CHECKING

from my.config import pocket as user_config

from .core import Paths


@dataclass
class pocket(user_config):
    '''
    Uses [[https://github.com/karlicoss/pockexport][pockexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths


from .core.cfg import make_config

config = make_config(pocket)


try:
    from pockexport import dal
except ModuleNotFoundError as e:
    from my.core.hpi_compat import pre_pip_dal_handler

    dal = pre_pip_dal_handler('pockexport', e, config, requires=REQUIRES)

############################

Article = dal.Article

from collections.abc import Iterable, Sequence


# todo not sure if should be defensive against empty?
def _dal() -> dal.DAL:
    from .core import get_files
    inputs = get_files(config.export_path)
    return dal.DAL(inputs)


def articles() -> Iterable[Article]:
    yield from _dal().articles()


from .core import Stats, stat


def stats() -> Stats:
    from itertools import chain

    from more_itertools import ilen
    return {
        **stat(articles),
        'highlights': ilen(chain.from_iterable(a.highlights for a in articles())),
    }


# todo deprecate?
if not TYPE_CHECKING:
    # "deprecate" by hiding from mypy
    def get_articles() -> Sequence[Article]:
        return list(articles())
