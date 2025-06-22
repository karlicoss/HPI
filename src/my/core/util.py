from __future__ import annotations

import os
import pkgutil
import sys
from collections.abc import Iterable
from itertools import chain
from pathlib import Path
from types import ModuleType

from .discovery_pure import HPIModule, _is_not_module_src, has_stats, ignored


def modules() -> Iterable[HPIModule]:
    import my

    yield from _iter_all_importables(my)


__NOT_HPI_MODULE__ = 'Import this to mark a python file as a helper, not an actual HPI module'
from .discovery_pure import NOT_HPI_MODULE_VAR

assert NOT_HPI_MODULE_VAR in globals()  # check name consistency


def is_not_hpi_module(module: str) -> str | None:
    '''
    None if a module, otherwise returns reason
    '''
    import importlib.util

    path: str | None = None
    try:
        # TODO annoying, this can cause import of the parent module?
        spec = importlib.util.find_spec(module)
        assert spec is not None
        path = spec.origin
    except Exception:
        # todo a bit misleading.. it actually shouldn't import in most cases, it's just the weird parent module import thing
        return "import error (possibly missing config entry)"  # todo add exc message?
    assert path is not None  # not sure if can happen?
    if _is_not_module_src(Path(path)):
        return f"marked explicitly (via {NOT_HPI_MODULE_VAR})"

    if not has_stats(Path(path)):
        return "has no 'stats()' function"
    return None


# todo reuse in readme/blog post
# borrowed from https://github.com/sanitizers/octomachinery/blob/24288774d6dcf977c5033ae11311dbff89394c89/tests/circular_imports_test.py#L22-L55
def _iter_all_importables(pkg: ModuleType) -> Iterable[HPIModule]:
    # todo crap. why does it include some stuff three times??
    yield from chain.from_iterable(
        _discover_path_importables(Path(p), pkg.__name__)
        # todo might need to handle __path__ for individual modules too?
        # not sure why __path__ was duplicated, but it did happen..
        for p in set(pkg.__path__)
    )


def _discover_path_importables(pkg_pth: Path, pkg_name: str) -> Iterable[HPIModule]:
    """Yield all importables under a given path and package."""

    from .core_config import config  # noqa: F401

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
        pkg_pref = '.'.join((pkg_name, *rel_pt.parts))

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


def _walk_packages(path: Iterable[str], prefix: str = '', onerror=None) -> Iterable[HPIModule]:
    """
    Modified version of https://github.com/python/cpython/blob/d50a0700265536a20bcce3fb108c954746d97625/Lib/pkgutil.py#L53,
    to avoid importing modules that are skipped
    """
    from .core_config import config

    def seen(p, m={}) -> bool:  # noqa: B006
        if p in m:
            return True
        m[p] = True  # noqa: RET503
        return False

    for info in pkgutil.iter_modules(path, prefix):
        mname = info.name
        if mname is None:
            # why would it be? anyway makes mypy happier
            continue

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

        else:  # active is True
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
            yield from _walk_packages(path, mname + '.', onerror)


# deprecate?
def get_modules() -> list[HPIModule]:
    return list(modules())


### tests start

## FIXME: add test when there is an import error -- should be defensive and yield exception


def test_module_detection() -> None:
    from .core_config import _reset_config as reset

    with reset() as cc:
        cc.disabled_modules = ['my.location.*', 'my.body.*', 'my.workouts.*', 'my.private.*']
        mods = {m.name: m for m in modules()}
        assert mods['my.demo'].skip_reason == "has no 'stats()' function"

    with reset() as cc:
        cc.disabled_modules = ['my.location.*', 'my.body.*', 'my.workouts.*', 'my.private.*', 'my.lastfm']
        cc.enabled_modules = ['my.demo']
        mods = {m.name: m for m in modules()}

        assert mods['my.demo'].skip_reason is None  # not skipped
        assert mods['my.lastfm'].skip_reason == "suppressed in the user config"


def test_good_modules(tmp_path: Path) -> None:
    badp = tmp_path / 'good'
    par = badp / 'my'
    par.mkdir(parents=True)

    (par / 'good.py').write_text('def stats(): pass')
    (par / 'disabled.py').write_text('''
from my.core import __NOT_HPI_MODULE__
''')
    (par / 'nostats.py').write_text('''
# no stats!
''')

    import sys

    orig_path = list(sys.path)
    try:
        sys.path.insert(0, str(badp))
        good     = is_not_hpi_module('my.good')
        disabled = is_not_hpi_module('my.disabled')
        nostats  = is_not_hpi_module('my.nostats')
    finally:
        sys.path = orig_path

    assert good is None # good module!
    assert disabled is not None
    assert 'marked explicitly' in disabled
    assert nostats is not None
    assert 'stats' in nostats


def test_bad_modules(tmp_path: Path) -> None:
    xx = tmp_path / 'precious_data'
    xx.write_text('some precious data')
    badp = tmp_path / 'bad'
    par = badp / 'my'
    par.mkdir(parents=True)

    (par / 'malicious.py').write_text(f'''
from pathlib import Path
Path(r'{xx}').write_text('aaand your data is gone!')

raise RuntimeError("FAIL ON IMPORT! naughty.")

def stats():
    return [1, 2, 3]
''')

    import sys

    orig_path = list(sys.path)
    try:
        sys.path.insert(0, str(badp))
        res = is_not_hpi_module('my.malicious')
    finally:
        sys.path = orig_path
    # shouldn't crash at least
    assert res is None  # good as far as discovery is concerned
    assert xx.read_text() == 'some precious data'  # make sure module wasn't evaluated


### tests end
