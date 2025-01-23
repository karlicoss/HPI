"""
Monzo transactions data (using https://github.com/karlicoss/monzoexport )
"""
REQUIRES = [
    'git+https://github.com/karlicoss/monzoexport',
]

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from my.core import (
    Paths,
    get_files,
    make_logger,
)

import my.config  # isort: skip


@dataclass
class config(my.config.monzo.monzoexport):
    '''
    Uses [[https://github.com/karlicoss/monzoexport][ghexport]] outputs.
    '''

    export_path: Paths
    '''path[s]/glob to the exported JSON data'''


logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


import monzoexport.dal as dal


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


def transactions() -> Iterator[dal.MonzoTransaction]:
    return _dal().transactions()
