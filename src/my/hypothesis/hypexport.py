"""
[[https://hypothes.is][Hypothes.is]] highlights and annotations

Reads the standard Hypothes.is JSON export format used by [[https://github.com/karlicoss/hypexport][hypexport]].
"""

REQUIRES = [
    'hypexport @ git+https://github.com/karlicoss/hypexport',
]

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import cast

from hypexport import dal

from my.core import Paths, Res, Stats, get_files, stat, warnings


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to hypexport JSON files."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import hypothesis as user_config

    if hasattr(user_config, 'hypexport'):

        class combined_config(user_config.hypexport, Config):
            pass

        return combined_config()

    warnings.high('The flat Hypothesis config is deprecated. Use my.config.hypothesis.hypexport.export_path instead.')
    return cast(Config, user_config())


DAL = dal.DAL
Highlight = dal.Highlight
Page = dal.Page


def inputs() -> Sequence[Path]:
    return get_files(make_config().export_path)


def _dal() -> DAL:
    return DAL(inputs())


# TODO they are in reverse chronological order...
def highlights() -> Iterator[Res[Highlight]]:
    return _dal().highlights()


def pages() -> Iterator[Res[Page]]:
    return _dal().pages()


def stats() -> Stats:
    return {
        **stat(highlights),
        **stat(pages),
    }
