from pathlib import Path
from itertools import chain
from importlib import import_module
import os
import pkgutil
import re
import sys
from typing import List, Iterable, NamedTuple, Optional


class HPIModule(NamedTuple):
    name: str
    skip_reason: Optional[str]


def modules() -> Iterable[HPIModule]:
    import my
    for m in _iter_all_importables(my):
        yield m


def ignored(m: str) -> bool:
    excluded = [
        'core.*',
        'config.*',
        ## todo move these to core
        'kython.*',
        'mycfg_stub',
        ##
    ]
    exs = '|'.join(excluded)
    return re.match(f'^my.({exs})$', m) is not None


def get_stats(module: str):
    # todo detect via ast?
    try:
        mod = import_module(module)
    except Exception as e:
        return None

    return getattr(mod, 'stats', None)


__NOT_HPI_MODULE__ = 'Import this to mark a python file as a helper, not an actual HPI module'

def has_not_module_flag(module: str) -> bool:
    # if module == 'my.books.kobo':
    #     breakpoint()
    #     pass
    try:
        mod = import_module(module)
    except Exception as e:
        return False

    return any(x is __NOT_HPI_MODULE__ for x in vars(mod).values())

def is_not_hpi_module(module: str) -> Optional[str]:
    # None if a module, otherwise returns reason
    if has_not_module_flag(module):
        return "marked explicitly (via __NOT_HPI_MODULE__)"
    stats = get_stats(module)
    if stats is None:
        return "has no 'stats()' function"
    return None

# todo reuse in readme/blog post
# borrowed from https://github.com/sanitizers/octomachinery/blob/24288774d6dcf977c5033ae11311dbff89394c89/tests/circular_imports_test.py#L22-L55
def _iter_all_importables(pkg) -> Iterable[HPIModule]:
    # todo crap. why does it include some stuff three times??
    yield from chain.from_iterable(
        _discover_path_importables(Path(p), pkg.__name__)
        # todo might need to handle __path__ for individual modules too?
        # not sure why __path__ was duplicated, but it did happen..
        for p in set(pkg.__path__)
    )


def _discover_path_importables(pkg_pth, pkg_name) -> Iterable[HPIModule]:
    from .core_config import config

    """Yield all importables under a given path and package."""
    for dir_path, dirs, file_names in os.walk(pkg_pth):
        file_names.sort()
        # NOTE: sorting dirs in place is intended, it's the way you're supposed to do it with os.walk
        dirs.sort()

        pkg_dir_path = Path(dir_path)

        if pkg_dir_path.parts[-1] == '__pycache__':
            continue

        if all(Path(_).suffix != '.py' for _ in file_names):
            continue

        rel_pt = pkg_dir_path.relative_to(pkg_pth)
        pkg_pref = '.'.join((pkg_name, ) + rel_pt.parts)

        yield from _walk_packages(
            (str(pkg_dir_path), ), prefix=f'{pkg_pref}.',
        )
        # TODO might need to make it defensive and yield Exception (otherwise hpi doctor might fail for no good reason)
        # use onerror=?

# ignored explicitly     -> not HPI
# if enabled  in config  -> HPI
# if disabled in config  -> HPI
# otherwise, check for stats
# recursion is relied upon using .*
# TODO when do we need to recurse?


def _walk_packages(path=None, prefix='', onerror=None) -> Iterable[HPIModule]:
    '''
    Modified version of https://github.com/python/cpython/blob/d50a0700265536a20bcce3fb108c954746d97625/Lib/pkgutil.py#L53,
    to alvoid importing modules that are skipped
    '''
    from .core_config import config

    def seen(p, m={}):
        if p in m:
            return True
        m[p] = True

    for info in pkgutil.iter_modules(path, prefix):
        mname = info.name

        if ignored(mname):
            # not sure if need to yield?
            continue

        active = config._is_module_active(mname)
        skip_reason = None
        if active is False:
            skip_reason = 'suppressed in the user config'
        elif active is None:
            # unspecified by the user, rely on other means
            is_not_module = is_not_hpi_module(mname)
            if is_not_module is not None:
                skip_reason = is_not_module

        else: # active is True
            # nothing to do, enabled explicitly
            pass

        yield HPIModule(
            name=mname,
            skip_reason=skip_reason,
        )
        if not info.ispkg:
            continue

        recurse = config._is_module_active(mname + '.')
        if not recurse:
            continue

        try:
            __import__(mname)
        except ImportError:
            if onerror is not None:
                onerror(mname)
        except Exception:
            if onerror is not None:
                onerror(mname)
            else:
                raise
        else:
            path = getattr(sys.modules[mname], '__path__', None) or []
            # don't traverse path items we've seen before
            path = [p for p in path if not seen(p)]
            yield from _walk_packages(path, mname+'.', onerror)

# deprecate?
def get_modules() -> List[HPIModule]:
    return list(modules())



### tests start

## FIXME: add test when there is an import error -- should be defensive and yield exception

def test_module_detection() -> None:
    from .core_config import _reset_config as reset
    with reset() as cc:
        cc.disabled_modules = ['my.location.*', 'my.body.*', 'my.workouts.*', 'my.private.*']
        mods = {m.name: m for m in modules()}
        assert mods['my.demo']  .skip_reason == "has no 'stats()' function"

    with reset() as cc:
        cc.disabled_modules = ['my.location.*', 'my.body.*', 'my.workouts.*', 'my.private.*', 'my.lastfm']
        cc.enabled_modules  = ['my.demo']
        mods = {m.name: m for m in modules()}

        assert mods['my.demo']  .skip_reason is None # not skipped
        assert mods['my.lastfm'].skip_reason == "suppressed in the user config"



### tests end
