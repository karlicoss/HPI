"""
[[https://hypothes.is][Hypothes.is]] highlights and annotations
"""

REQUIRES = [
    'hypexport @ git+https://github.com/karlicoss/hypexport',
]
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from my.core import (
    Paths,
    Res,
    Stats,
    get_files,
    stat,
)
from my.core.cfg import make_config

import my.config  # isort: skip


@dataclass
class hypothesis(my.config.hypothesis):
    '''
    Uses [[https://github.com/karlicoss/hypexport][hypexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths


config = make_config(hypothesis)


from hypexport import dal

DAL = dal.DAL
Highlight = dal.Highlight
Page = dal.Page


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


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
