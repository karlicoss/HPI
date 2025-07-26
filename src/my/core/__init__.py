# this file only keeps the most common & critical types/utility functions

from .cfg import make_config
from .common import PathIsh, Paths, get_files
from .error import Res, notnone, unwrap
from .logging import make_logger
from .stats import Stats, stat
from .types import (
    Json,
    datetime_aware,
    datetime_naive,
)
from .util import __NOT_HPI_MODULE__
from .utils.itertools import warn_if_empty

__all__ = [
    '__NOT_HPI_MODULE__',
    'Json',
    'Path',
    'PathIsh',
    'Paths',
    'Res',
    'Stats',
    'dataclass',
    'datetime_aware',
    'datetime_naive',
    'get_files',
    'make_config',
    'make_logger',
    'notnone',
    'stat',
    'unwrap',
    'warn_if_empty',
]


##
from .internal import warn_if_not_using_src_layout

warn_if_not_using_src_layout(path=__path__)

del warn_if_not_using_src_layout
##


## experimental for now
# you could put _init_hook.py next to your private my/config
# that way you can configure logging/warnings/env variables on every HPI import
try:
    import my._init_hook  # type: ignore[import-not-found]  # noqa: F401
except:
    pass
##


## legacy imports, preserved for runtime backwards compatibility
from typing import TYPE_CHECKING

if not TYPE_CHECKING:
    from .compat import deprecated

    @deprecated('use make_logger instead')
    def LazyLogger(*args, **kwargs):
        return make_logger(*args, **kwargs)

    # this will be in stdlib in 3.11, so discourage importing from my.core
    @deprecated('use typing.assert_never or my.compat.assert_never')
    def assert_never(*args, **kwargs):
        from . import compat

        return compat.assert_never(*args, **kwargs)  # ty: ignore[type-assertion-failure]

    del deprecated

__all__ += [
    'LazyLogger',
    'assert_never',
]


if not TYPE_CHECKING:
    # we used to keep these here for brevity, but feels like it only adds confusion,
    #  e.g. suggest that we perhaps somehow modify builtin behaviour or whatever
    #  so best to prefer explicit behaviour
    from dataclasses import dataclass
    from pathlib import Path

del TYPE_CHECKING
##
