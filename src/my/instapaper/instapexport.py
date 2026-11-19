"""
[[https://www.instapaper.com][Instapaper]] bookmarks, highlights and annotations

Reads JSON exports from [[https://github.com/karlicoss/instapexport][instapexport]].
"""

REQUIRES = [
    'instapexport @ git+https://github.com/karlicoss/instapexport',
]

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast

from instapexport import dal

from my.core import Paths, Stats, get_files, stat, warnings


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to instapexport JSON files."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import instapaper as user_config

    if hasattr(user_config, 'instapexport'):

        class combined_config(user_config.instapexport, Config):
            pass

        return combined_config()

    warnings.high(
        'The flat Instapaper config is deprecated. Use my.config.instapaper.instapexport.export_path instead.'
    )
    return cast(Config, user_config())


Highlight = dal.Highlight
Bookmark = dal.Bookmark
Page = dal.Page


def inputs() -> Sequence[Path]:
    return get_files(make_config().export_path)


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


def pages() -> Iterable[Page]:
    return _dal().pages()


def stats() -> Stats:
    return stat(pages)


# TODO dunno, move this to private?
def is_todo(hl: Highlight) -> bool:
    note = hl.note or ''
    note = note.lstrip().lower()
    return note.startswith('todo')


get_pages = pages  # todo also deprecate..
