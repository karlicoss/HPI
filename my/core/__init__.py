# this file only keeps the most common & critical types/utility functions
from .common import get_files, PathIsh, Paths
from .common import Json
from .common import warn_if_empty
from .common import stat, Stats
from .common import datetime_naive, datetime_aware
from .common import assert_never

from .cfg import make_config
from .error import Res, unwrap
from .logging import make_logger, LazyLogger
from .util import __NOT_HPI_MODULE__


# just for brevity in modules
# todo not sure about these.. maybe best to rely on regular imports.. perhaps compare?
from dataclasses import dataclass
from pathlib import Path


__all__ = [
    'get_files', 'PathIsh', 'Paths',
    'Json',
    'make_logger',
    'LazyLogger',  # legacy import
    'warn_if_empty',
    'stat', 'Stats',
    'datetime_aware', 'datetime_naive',
    'assert_never',

    'make_config',

    '__NOT_HPI_MODULE__',

    'Res', 'unwrap',

    'dataclass', 'Path',
]


## experimental for now
# you could put _init_hook.py next to your private my/config
# that way you can configure logging/warnings/env variables on every HPI import
try:
    import my._init_hook  # type: ignore[import-not-found]
except:
    pass
##
