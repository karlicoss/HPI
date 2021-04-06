'''
ActivityWatch data
'''

REQUIRES = [
    'git+https://github.com/hpi/activitywatch',
]

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Iterable

from .core import Paths, get_files

from my.config import activitywatch as user_config

@dataclass
class activitywatch(user_config):
    # paths[s]/glob to the exported JSON data
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(activitywatch.export_path)


import activitywatch.dal as dal


def windowEvents():
    _dal = dal.DAL(inputs())
    yield from _dal.events('window')

