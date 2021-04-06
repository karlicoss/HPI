'''
Withings data
'''

REQUIRES = [
    'git+https://github.com/hpi/withings',
]

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Iterable

from .core import Paths, get_files

from my.config import withings as user_config

@dataclass
class withings(user_config):
    # paths[s]/glob to the exported JSON data
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(withings.export_path)


import withings.dal as dal


def measurements():
    _dal = dal.DAL(inputs())
    yield from _dal.measurements()
