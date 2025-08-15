"""
[[https://getpocket.com][Pocket]] bookmarks and highlights
"""

REQUIRES = [
    'pockexport @ git+https://github.com/karlicoss/pockexport',
]
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from my.core import Paths, Stats, get_files, stat
from my.core.cfg import make_config

from my.config import pocket as user_config  # isort: skip


@dataclass
class pocket(user_config):
    '''
    Uses [[https://github.com/karlicoss/pockexport][pockexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths


config = make_config(pocket)


try:
    from pockexport import dal
except ModuleNotFoundError as e:
    from my.core.hpi_compat import pre_pip_dal_handler

    dal = pre_pip_dal_handler('pockexport', e, config, requires=REQUIRES)

############################

Article = dal.Article


# todo not sure if should be defensive against empty?
def _dal() -> dal.DAL:
    inputs = get_files(config.export_path)
    return dal.DAL(inputs)


def articles() -> Iterable[Article]:
    yield from _dal().articles()


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
