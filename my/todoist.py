'''
Todoist data
'''

REQUIRES = [
    'git+https://github.com/hpi/todoist'
]

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Iterable

from .core import Paths, get_files

from my.config import todoist as user_config

@dataclass
class todoist(user_config):
    # paths[s]/glob to the exported JSON data
    export_path: Paths


def inputs() -> Sequence[Path]:
    return get_files(todoist.export_path)


import todoist.dal as dal


def projects():
    _dal = dal.DAL(inputs())
    yield from _dal.projects()

def tasks():
    _dal = dal.DAL(inputs())
    yield from _dal.tasks()

