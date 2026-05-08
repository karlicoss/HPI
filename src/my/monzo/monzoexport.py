"""
Monzo transactions data (using https://github.com/karlicoss/monzoexport )
"""
REQUIRES = [
    'monzoexport @ git+https://github.com/karlicoss/monzoexport',
]

from abc import abstractmethod
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Protocol

from my.core import Paths, get_files, make_logger

import my.config  # isort: skip


class Config(Protocol):
    '''
    Uses [[https://github.com/karlicoss/monzoexport][ghexport]] outputs.
    '''

    @property
    @abstractmethod
    def export_path(self) -> Paths:
        '''path[s]/glob to the exported JSON data'''
        raise NotImplementedError


class config(my.config.monzo.monzoexport, Config):
    pass


logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


import monzoexport.dal as dal


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


def transactions() -> Iterator[dal.MonzoTransaction]:
    return _dal().transactions()
