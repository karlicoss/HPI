'''
Some backwards compatibility stuff/deprecation helpers
'''
import sys
from types import ModuleType

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


import sqlite3
def sqlite_backup(*, source: sqlite3.Connection, dest: sqlite3.Connection, **kwargs) -> None:
    if sys.version_info[:2] >= (3, 7):
        source.backup(dest, **kwargs)
    else:
        # https://stackoverflow.com/a/10856450/706389
        import io
        tempfile = io.StringIO()
        for line in source.iterdump():
            tempfile.write('%s\n' % line)
        tempfile.seek(0)

        dest.cursor().executescript(tempfile.read())
        dest.commit()


# can remove after python3.9
def removeprefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


# can remove after python3.8
if sys.version_info[:2] >= (3, 8):
    from functools import cached_property
else:
    from typing import TypeVar, Callable
    Cl = TypeVar('Cl')
    R = TypeVar('R')

    def cached_property(f: Callable[[Cl], R]) -> R:
        import functools
        return property(functools.lru_cache(maxsize=1)(f)) # type: ignore
    del Cl
    del R


from typing import TYPE_CHECKING


if sys.version_info[:2] >= (3, 8):
    from typing import Literal
else:
    if TYPE_CHECKING:
        from typing_extensions import Literal
    else:
        # erm.. I guess as long as it's not crashing, whatever...
        class _Literal:
            def __getitem__(self, args):
                pass
        Literal = _Literal()


if sys.version_info[:2] >= (3, 8):
    from typing import Protocol
else:
    if TYPE_CHECKING:
        from typing_extensions import Protocol  # type: ignore[misc]
    else:
        # todo could also use NamedTuple?
        Protocol = object


if sys.version_info[:2] >= (3, 8):
    from typing import TypedDict
else:
    if TYPE_CHECKING:
        from typing_extensions import TypedDict  # type: ignore[misc]
    else:
        from typing import Dict
        TypedDict = Dict
