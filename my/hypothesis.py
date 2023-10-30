"""
[[https://hypothes.is][Hypothes.is]] highlights and annotations
"""
REQUIRES = [
    'git+https://github.com/karlicoss/hypexport',
]
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence, TYPE_CHECKING

from my.core import (
    get_files,
    stat,
    Paths,
    Res,
    Stats,
)
from my.core.cfg import make_config
from my.core.hpi_compat import always_supports_sequence
import my.config


@dataclass
class hypothesis(my.config.hypothesis):
    '''
    Uses [[https://github.com/karlicoss/hypexport][hypexport]] outputs
    '''

    # paths[s]/glob to the exported JSON data
    export_path: Paths


config = make_config(hypothesis)


try:
    from hypexport import dal
except ModuleNotFoundError as e:
    from my.core.hpi_compat import pre_pip_dal_handler

    dal = pre_pip_dal_handler('hypexport', e, config, requires=REQUIRES)


Highlight = dal.Highlight
Page = dal.Page


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


# TODO they are in reverse chronological order...
def highlights() -> Iterator[Res[Highlight]]:
    return always_supports_sequence(_dal().highlights())


def pages() -> Iterator[Res[Page]]:
    return always_supports_sequence(_dal().pages())


def stats() -> Stats:
    return {
        **stat(highlights),
        **stat(pages),
    }


if not TYPE_CHECKING:
    # "deprecate" by hiding from mypy
    get_highlights = highlights
    get_pages = pages
