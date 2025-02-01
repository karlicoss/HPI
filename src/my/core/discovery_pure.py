'''
The idea of this module is to avoid imports of external HPI modules and code evaluation via ast module etc.

This potentially allows it to be:

- robust: can discover modules that can't be imported, generally makes it foolproof
- faster: importing is slow and with tens of modules can be noteiceable
- secure: can be executed in a sandbox & used during setup

It should be free of external modules, importlib, exec, etc. etc.
'''

from __future__ import annotations

REQUIRES = 'REQUIRES'
NOT_HPI_MODULE_VAR = '__NOT_HPI_MODULE__'

###

import ast
import logging
import os
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, NamedTuple, Optional, cast

'''
None means that requirements weren't defined (different from empty requirements)
'''
Requires = Optional[Sequence[str]]


class HPIModule(NamedTuple):
    name: str
    skip_reason: str | None
    doc: str | None = None
    file: Path | None = None
    requires: Requires = None
    legacy: str | None = None  # contains reason/deprecation warning


def ignored(m: str) -> bool:
    excluded = [
        # legacy stuff left for backwards compatibility
        'core.*',
        'config.*',
    ]
    exs = '|'.join(excluded)
    return re.match(f'^my.({exs})$', m) is not None


def has_stats(src: Path) -> bool:
    # todo make sure consistent with get_stats?
    return _has_stats(src.read_text())


def _has_stats(code: str) -> bool:
    a: ast.Module = ast.parse(code)
    for x in a.body:
        try:  # maybe assign
            [tg] = cast(Any, x).targets
            if tg.id == 'stats':
                return True
        except:
            pass
        try:  # maybe def?
            name = cast(Any, x).name
            if name == 'stats':
                return True
        except:
            pass
    return False


def _is_not_module_src(src: Path) -> bool:
    a: ast.Module = ast.parse(src.read_text())
    return _is_not_module_ast(a)


def _is_not_module_ast(a: ast.Module) -> bool:
    marker = NOT_HPI_MODULE_VAR
    return any(
        getattr(node, 'name', None) == marker  # direct definition
        or any(getattr(n, 'name', None) == marker for n in getattr(node, 'names', []))  # import from
        for node in a.body
    )


def _is_legacy_module(a: ast.Module) -> bool:
    marker = 'handle_legacy_import'
    return any(
        getattr(node, 'name', None) == marker  # direct definition
        or any(getattr(n, 'name', None) == marker for n in getattr(node, 'names', []))  # import from
        for node in a.body
    )


# todo should be defensive? not sure
def _extract_requirements(a: ast.Module) -> Requires:
    # find the assignment..
    for x in a.body:
        if not isinstance(x, ast.Assign):
            continue
        tg = x.targets
        if len(tg) != 1:
            continue
        t = tg[0]
        # could be Subscript.. so best to keep dynamic
        id_ = getattr(t, 'id', None)
        if id_ != REQUIRES:
            continue
        vals = x.value
        # could be List/Tuple/Set?
        elts = getattr(vals, 'elts', None)
        if elts is None:
            continue
        deps = []
        for c in elts:
            if isinstance(c, ast.Constant):
                deps.append(c.value)
            else:
                raise RuntimeError(f"Expecting string constants only in {REQUIRES} declaration")
        return tuple(deps)
    return None


# todo should probably be more defensive..
def all_modules() -> Iterable[HPIModule]:
    """
    Return all importable modules under all items in the 'my' namespace package

    Note: This returns all modules under all roots - if you have
    several overlays (multiple items in my.__path__ and you've overridden
    modules), this can return multiple HPIModule objects with the same
    name. It should respect import order, as we're traversing
    in my.__path__ order, so module_by_name should still work
    and return the correctly resolved module, but all_modules
    can have duplicates
    """
    for my_root in _iter_my_roots():
        yield from _modules_under_root(my_root)


def _iter_my_roots() -> Iterable[Path]:
    import my  # doesn't import any code, because of namespace package

    paths: list[str] = list(my.__path__)
    if len(paths) == 0:
        # should probably never happen?, if this code is running, it was imported
        # because something was added to __path__ to match this name
        raise RuntimeError("my.__path__ was empty, try re-installing HPI?")
    else:
        yield from map(Path, paths)


def _modules_under_root(my_root: Path) -> Iterable[HPIModule]:
    """
    Experimental version, which isn't importing the modules, making it more robust and safe.
    """
    for f in sorted(my_root.rglob('*.py')):
        if f.is_symlink():
            continue  # meh
        mp = f.relative_to(my_root.parent)
        if mp.name == '__init__.py':
            mp = mp.parent
        m = str(mp.with_suffix('')).replace(os.sep, '.')
        if ignored(m):
            continue
        a: ast.Module = ast.parse(f.read_text())

        # legacy modules are 'forced' to be modules so 'hpi module install' still works for older modules
        # a bit messy, will think how to fix it properly later
        legacy_module = _is_legacy_module(a)
        if _is_not_module_ast(a) and not legacy_module:
            continue
        doc = ast.get_docstring(a, clean=False)

        requires: Requires = None
        try:
            requires = _extract_requirements(a)
        except Exception as e:
            logging.exception(e)

        legacy = f'{m} is DEPRECATED. Please refer to the module documentation.' if legacy_module else None

        yield HPIModule(
            name=m,
            skip_reason=None,
            doc=doc,
            file=f.relative_to(my_root.parent),
            requires=requires,
            legacy=legacy,
        )


def module_by_name(name: str) -> HPIModule:
    for m in all_modules():
        if m.name == name:
            return m
    raise RuntimeError(f'No such module: {name}')


### tests


def test() -> None:
    # TODO this should be a 'sanity check' or something
    assert len(list(all_modules())) > 10  # kinda arbitrary


def test_demo() -> None:
    demo = module_by_name('my.demo')
    assert demo.doc is not None
    assert demo.file == Path('my', 'demo.py')
    assert demo.requires is None


def test_excluded() -> None:
    for m in all_modules():
        assert 'my.core.' not in m.name


def test_requires() -> None:
    photos = module_by_name('my.photos.main')
    r = photos.requires
    assert r is not None
    assert len(r) == 2  # fragile, but ok for now


def test_legacy_modules() -> None:
    # shouldn't crash
    module_by_name('my.reddit')
    module_by_name('my.fbmessenger')


def test_pure() -> None:
    """
    We want to keep this module clean of other HPI imports
    """
    # this uses string concatenation here to prevent
    # these tests from testing against themselves
    src = Path(__file__).read_text()
    # 'import my' is allowed, but
    # dont allow anything other HPI modules
    assert re.findall('import ' + r'my\.\S+', src, re.MULTILINE) == []
    assert 'from ' + 'my' not in src


def test_has_stats() -> None:
    assert not _has_stats('')
    assert not _has_stats('x = lambda : whatever')

    assert _has_stats('''
def stats():
    pass
''')

    assert _has_stats('''
stats = lambda: "something"
''')

    assert _has_stats('''
stats = other_function
    ''')
