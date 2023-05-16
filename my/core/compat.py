'''
Some backwards compatibility stuff/deprecation helpers
'''
import sys
from types import ModuleType
from typing import TYPE_CHECKING

from . import warnings
from .common import LazyLogger


logger = LazyLogger('my.core.compat')


def pre_pip_dal_handler(
        name: str,
        e: ModuleNotFoundError,
        cfg,
        requires=[],
) -> ModuleType:
    '''
    https://github.com/karlicoss/HPI/issues/79
    '''
    if e.name != name:
        # the module itself was imported, so the problem is with some dependencies
        raise e
    try:
        dal = _get_dal(cfg, name)
        warnings.high(f'''
Specifying modules' dependencies in the config or in my/config/repos is deprecated!
Please install {' '.join(requires)} as PIP packages (see the corresponding README instructions).
'''.strip(), stacklevel=2)
    except ModuleNotFoundError:
        dal = None

    if dal is None:
        # probably means there was nothing in the old config in the first place
        # so we should raise the original exception
        raise e
    return dal


def _get_dal(cfg, module_name: str):
    mpath = getattr(cfg, module_name, None)
    if mpath is not None:
        from .common import import_dir
        return import_dir(mpath, '.dal')
    else:
        from importlib import import_module
        return import_module(f'my.config.repos.{module_name}.dal')


import os
windows = os.name == 'nt'


# keeping just for backwards compatibility, used to have compat implementation for 3.6
import sqlite3
def sqlite_backup(*, source: sqlite3.Connection, dest: sqlite3.Connection, **kwargs) -> None:
    source.backup(dest, **kwargs)


# can remove after python3.9
def removeprefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


## used to have compat function before 3.8 for these
from functools import cached_property
from typing import Literal, Protocol, TypedDict
##


if sys.version_info[:2] >= (3, 10):
    from typing import ParamSpec
else:
    if TYPE_CHECKING:
        from typing_extensions import ParamSpec
    else:
        from typing import NamedTuple, Any
        # erm.. I guess as long as it's not crashing, whatever...
        class _ParamSpec:
            def __call__(self, args):
                class _res:
                    args = None
                    kwargs = None
                return _res
        ParamSpec = _ParamSpec()


# bisect_left doesn't have a 'key' parameter (which we use)
# till python3.10
if sys.version_info[:2] <= (3, 9):
    from typing import List, TypeVar, Any, Optional, Callable
    X = TypeVar('X')
    # copied from python src
    def bisect_left(a: List[Any], x: Any, lo: int=0, hi: Optional[int]=None, *, key: Optional[Callable[..., Any]]=None) -> int:
        if lo < 0:
            raise ValueError('lo must be non-negative')
        if hi is None:
            hi = len(a)
        # Note, the comparison uses "<" to match the
        # __lt__() logic in list.sort() and in heapq.
        if key is None:
            while lo < hi:
                mid = (lo + hi) // 2
                if a[mid] < x:
                    lo = mid + 1
                else:
                    hi = mid
        else:
            while lo < hi:
                mid = (lo + hi) // 2
                if key(a[mid]) < x:
                    lo = mid + 1
                else:
                    hi = mid
        return lo
else:
    from bisect import bisect_left
