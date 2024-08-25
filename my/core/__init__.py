# this file only keeps the most common & critical types/utility functions
from typing import TYPE_CHECKING

from .cfg import make_config
from .common import PathIsh, Paths, get_files
from .compat import assert_never
from .error import Res, unwrap, notnone
from .logging import (
    make_logger,
)
from .stats import Stats, stat
from .types import (
    Json,
    datetime_aware,
    datetime_naive,
)
from .util import __NOT_HPI_MODULE__
from .utils.itertools import warn_if_empty

LazyLogger = make_logger  # TODO deprecate this in favor of make_logger


if not TYPE_CHECKING:
    # we used to keep these here for brevity, but feels like it only adds confusion,
    #  e.g. suggest that we perhaps somehow modify builtin behaviour or whatever
    #  so best to prefer explicit behaviour
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
    'assert_never',  # TODO maybe deprecate from use in my.core? will be in stdlib soon

    'make_config',

    '__NOT_HPI_MODULE__',

    'Res', 'unwrap', 'notnone',

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
