'''
Levels Health data
'''

REQUIRES = [
    'git+https://github.com/hpi/levelshealth',
]

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Iterable

from .core import Paths, get_files

from my.config import levelshealth as user_config

@dataclass
class levelshealth(user_config):
    # paths[s]/glob to the exported JSON data
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(levelshealth.export_path)


import levelshealth.dal as dal


def glucoseScores():
    _dal = dal.DAL(inputs())
    yield from _dal.glucoseScores()

def zones():
    _dal = dal.DAL(inputs())
    yield from _dal.zones()

def streaks():
    _dal = dal.DAL(inputs())
    yield from _dal.streaks()

