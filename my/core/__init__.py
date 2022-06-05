# this file only keeps the most common & critical types/utility functions
from .common import get_files, PathIsh, Paths
from .common import Json
from .common import LazyLogger
from .common import warn_if_empty
from .common import stat, Stats
from .common import datetime_naive, datetime_aware
from .common import assert_never

from .cfg import make_config

from .util import __NOT_HPI_MODULE__

from .error import Res, unwrap


# just for brevity in modules
# todo not sure about these.. maybe best to rely on regular imports.. perhaps compare?
from dataclasses import dataclass
from pathlib import Path


__all__ = [
    'get_files', 'PathIsh', 'Paths',
    'Json',
    'LazyLogger',
    'warn_if_empty',
    'stat', 'Stats',
    'datetime_aware', 'datetime_naive',
    'assert_never',

    'make_config',

    '__NOT_HPI_MODULE__',

    'Res', 'unwrap',

    'dataclass', 'Path',
]
