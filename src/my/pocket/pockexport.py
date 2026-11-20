"""
[[https://getpocket.com][Pocket]] bookmarks and highlights

Reads JSON exports from [[https://github.com/karlicoss/pockexport][pockexport]].
"""

REQUIRES = [
    'pockexport @ git+https://github.com/karlicoss/pockexport',
]

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, cast

from pockexport import dal

from my.core import Paths, Stats, get_files, stat, warnings


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to pockexport JSON files."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import pocket as user_config

    if hasattr(user_config, 'pockexport'):

        class combined_config(user_config.pockexport, Config):
            pass

        return combined_config()

    warnings.high('The flat Pocket config is deprecated. Use my.config.pocket.pockexport.export_path instead.')
    return cast(Config, user_config())


Article = dal.Article


# todo not sure if should be defensive against empty?
def _dal() -> dal.DAL:
    inputs = get_files(make_config().export_path)
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
