"""
Contains various backwards compatibility/deprecation helpers relevant to HPI itself.
(as opposed to .compat module which implements compatibility between python versions)
"""

from __future__ import annotations

import inspect
import os
import re
from collections.abc import Iterator, Sequence
from types import ModuleType
from typing import TypeVar

from . import warnings


def handle_legacy_import(
    parent_module_name: str,
    legacy_submodule_name: str,
    parent_module_path: list[str],
) -> bool:
    ###
    # this is to trick mypy into treating this as a proper namespace package
    # should only be used for backwards compatibility on packages that are convernted into namespace & all.py pattern
    # - https://www.python.org/dev/peps/pep-0382/#namespace-packages-today
    # - https://github.com/karlicoss/hpi_namespace_experiment
    # - discussion here https://memex.zulipchat.com/#narrow/stream/279601-hpi/topic/extending.20HPI/near/269946944
    from pkgutil import extend_path

    parent_module_path[:] = extend_path(parent_module_path, parent_module_name)
    # 'this' source tree ends up first in the pythonpath when we extend_path()
    # so we need to move 'this' source tree towards the end to make sure we prioritize overlays
    parent_module_path[:] = parent_module_path[1:] + parent_module_path[:1]
    ###

    # allow stuff like 'import my.module.submodule' and such
    imported_as_parent = False

    # allow stuff like 'from my.module import submodule'
    importing_submodule = False

    # some hacky traceback to inspect the current stack
    # to see if the user is using the old style of importing
    for f in inspect.stack():
        # seems that when a submodule is imported, at some point it'll call some internal import machinery
        # with 'parent' set to the parent module
        # if parent module is imported first (i.e. in case of deprecated usage), it won't be the case
        args = inspect.getargvalues(f.frame)
        if args.locals.get('parent') == parent_module_name:
            imported_as_parent = True

        # this we can only detect from the code I guess
        line = '\n'.join(f.code_context or [])
        if re.match(rf'from\s+{parent_module_name}\s+import\s+{legacy_submodule_name}', line):
            importing_submodule = True

    # click sets '_HPI_COMPLETE' env var when it's doing autocompletion
    # otherwise, the warning will be printed every time you try to tab complete
    autocompleting_module_cli = "_HPI_COMPLETE" in os.environ

    is_legacy_import = not (imported_as_parent or importing_submodule)
    if is_legacy_import and not autocompleting_module_cli:
        warnings.high(
            f'''\
importing {parent_module_name} is DEPRECATED! \
Instead, import from {parent_module_name}.{legacy_submodule_name} or {parent_module_name}.all \
See https://github.com/karlicoss/HPI/blob/master/doc/MODULE_DESIGN.org#allpy for more info.
'''
        )
    return is_legacy_import


def pre_pip_dal_handler(
    name: str,
    e: ModuleNotFoundError,
    cfg,
    requires: Sequence[str] = (),
) -> ModuleType:
    '''
    https://github.com/karlicoss/HPI/issues/79
    '''
    if e.name != name:
        # the module itself was imported, so the problem is with some dependencies
        raise e
    try:
        dal = _get_dal(cfg, name)
        warnings.high(
            f'''
Specifying modules' dependencies in the config or in my/config/repos is deprecated!
Please install {' '.join(requires)} as PIP packages (see the corresponding README instructions).
'''.strip(),
            stacklevel=2,
        )
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
        from .utils.imports import import_dir

        return import_dir(mpath, '.dal')
    else:
        from importlib import import_module

        return import_module(f'my.config.repos.{module_name}.dal')


V = TypeVar('V')


# named to be kinda consistent with more_itertools, e.g. more_itertools.always_iterable
class always_supports_sequence(Iterator[V]):
    """
    Helper to make migration from Sequence/List to Iterable/Iterator type backwards compatible in runtime
    """

    def __init__(self, it: Iterator[V]) -> None:
        self._it = it
        self._list: list[V] | None = None
        self._lit: Iterator[V] | None = None

    def __iter__(self) -> Iterator[V]:  # noqa: PYI034
        if self._list is not None:
            self._lit = iter(self._list)
        return self

    def __next__(self) -> V:
        if self._list is not None:
            assert self._lit is not None
            delegate = self._lit
        else:
            delegate = self._it
        return next(delegate)

    def __getattr__(self, name):
        return getattr(self._it, name)

    @property
    def _aslist(self) -> list[V]:
        if self._list is None:
            qualname = getattr(self._it, '__qualname__', '<no qualname>')  # defensive just in case
            warnings.medium(f'Using {qualname} as list is deprecated. Migrate to iterative processing or call list() explicitly.')
            self._list = list(self._it)

            # this is necessary for list constructor to work correctly
            # since it's __iter__ first, then tries to compute length and then starts iterating...
            self._lit = iter(self._list)
        return self._list

    def __len__(self) -> int:
        return len(self._aslist)

    def __getitem__(self, i: int) -> V:
        return self._aslist[i]


def test_always_supports_sequence_list_constructor() -> None:
    exhausted = 0

    def it() -> Iterator[str]:
        nonlocal exhausted
        yield from ['a', 'b', 'c']
        exhausted += 1

    sit = always_supports_sequence(it())

    # list constructor is a bit special... it's trying to compute length if it's available to optimize memory allocation
    # so, what's happening in this case is
    # - sit.__iter__ is called
    # - sit.__len__  is called
    # - sit.__next__ is called
    res = list(sit)
    assert res == ['a', 'b', 'c']
    assert exhausted == 1

    res = list(sit)
    assert res == ['a', 'b', 'c']
    assert exhausted == 1  # this will iterate over 'cached' list now, so original generator is only exhausted once


def test_always_supports_sequence_indexing() -> None:
    exhausted = 0

    def it() -> Iterator[str]:
        nonlocal exhausted
        yield from ['a', 'b', 'c']
        exhausted += 1

    sit = always_supports_sequence(it())

    assert len(sit) == 3
    assert exhausted == 1

    assert sit[2] == 'c'
    assert sit[1] == 'b'
    assert sit[0] == 'a'
    assert exhausted == 1

    # a few tests to make sure list-like operations are working..
    assert list(sit) == ['a', 'b', 'c']
    assert [x for x in sit] == ['a', 'b', 'c']  # noqa: C416
    assert list(sit) == ['a', 'b', 'c']
    assert [x for x in sit] == ['a', 'b', 'c']  # noqa: C416
    assert exhausted == 1


def test_always_supports_sequence_next() -> None:
    exhausted = 0

    def it() -> Iterator[str]:
        nonlocal exhausted
        yield from ['a', 'b', 'c']
        exhausted += 1

    sit = always_supports_sequence(it())

    x = next(sit)
    assert x == 'a'
    assert exhausted == 0

    x = next(sit)
    assert x == 'b'
    assert exhausted == 0


def test_always_supports_sequence_iter() -> None:
    exhausted = 0

    def it() -> Iterator[str]:
        nonlocal exhausted
        yield from ['a', 'b', 'c']
        exhausted += 1

    sit = always_supports_sequence(it())

    for x in sit:
        assert x == 'a'
        break

    x = next(sit)
    assert x == 'b'

    assert exhausted == 0

    x = next(sit)
    assert x == 'c'
    assert exhausted == 0

    for _ in sit:
        raise RuntimeError  # shouldn't trigger, just exhaust the iterator
    assert exhausted == 1
