from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from glob import glob as do_glob
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    TypeVar,
    Union,
)

from . import compat, warnings

# some helper functions
# TODO start deprecating this? soon we'd be able to use Path | str syntax which is shorter and more explicit
PathIsh = Union[Path, str]

Paths = Union[Sequence[PathIsh], PathIsh]


DEFAULT_GLOB = '*'


def get_files(
    pp: Paths,
    glob: str = DEFAULT_GLOB,
    *,
    sort: bool = True,
    guess_compression: bool = True,
) -> tuple[Path, ...]:
    """
    Helper function to avoid boilerplate.

    Tuple as return type is a bit friendlier for hashing/caching, so hopefully makes sense
    """
    # TODO FIXME mm, some wrapper to assert iterator isn't empty?
    sources: list[Path]
    if isinstance(pp, Path):
        sources = [pp]
    elif isinstance(pp, str):
        if pp == '':
            # special case -- makes sense for optional data sources, etc
            return ()  # early return to prevent warnings etc
        sources = [Path(pp)]
    else:
        sources = [p if isinstance(p, Path) else Path(p) for p in pp]

    def caller() -> str:
        import traceback

        # TODO ugh. very flaky... -3 because [<this function>, get_files(), <actual caller>]
        return traceback.extract_stack()[-3].filename

    paths: list[Path] = []
    for src in sources:
        if src.parts[0] == '~':
            src = src.expanduser()
        # note: glob handled first, because e.g. on Windows asterisk makes is_dir unhappy
        gs = str(src)
        if '*' in gs:
            if glob != DEFAULT_GLOB:
                warnings.medium(f"{caller()}: treating {gs} as glob path. Explicit glob={glob} argument is ignored!")
            paths.extend(map(Path, do_glob(gs)))  # noqa: PTH207
        elif os.path.isdir(str(src)):  # noqa: PTH112
            # NOTE: we're using os.path here on purpose instead of src.is_dir
            # the reason is is_dir for archives might return True and then
            # this clause would try globbing insize the archives
            # this is generally undesirable (since modules handle archives themselves)

            # todo not sure if should be recursive?
            # note: glob='**/*.ext' works without any changes.. so perhaps it's ok as it is
            gp: Iterable[Path] = src.glob(glob)
            paths.extend(gp)
        else:
            assert src.exists(), src
            # todo assert matches glob??
            paths.append(src)

    if sort:
        paths = sorted(paths)

    if len(paths) == 0:
        # todo make it conditionally defensive based on some global settings
        warnings.high(
            f'''
{caller()}: no paths were matched against {pp}. This might result in missing data. Likely, the directory you passed is empty.
'''.strip()
        )
        # traceback is useful to figure out what config caused it?
        import traceback

        traceback.print_stack()

    if guess_compression:

        from kompress import CPath, is_compressed

        # note: ideally we'd just wrap everything in CPath for simplicity, however
        # - it doesn't preserve original Path/str if not compressed -- perhaps should fix __new__ method
        # - currently, rb mode isn't handled correctly? https://github.com/karlicoss/kompress/issues/22
        paths = [(CPath(p) if is_compressed(p) else p) for p in paths]
    return tuple(paths)


_R = TypeVar('_R')


# https://stackoverflow.com/a/5192374/706389
# NOTE: it was added to stdlib in 3.9 and then deprecated in 3.11
# seems that the suggested solution is to use custom decorator?
class classproperty(Generic[_R]):
    def __init__(self, f: Callable[..., _R]) -> None:
        self.f = f

    def __get__(self, obj, cls) -> _R:
        return self.f(cls)


def test_classproperty() -> None:
    from .compat import assert_type

    class C:
        @classproperty
        def prop(cls) -> str:
            return 'hello'

    res = C.prop
    assert_type(res, str)
    assert res == 'hello'


# hmm, this doesn't really work with mypy well..
# https://github.com/python/mypy/issues/6244
# class staticproperty(Generic[_R]):
#     def __init__(self, f: Callable[[], _R]) -> None:
#         self.f = f
#
#     def __get__(self) -> _R:
#         return self.f()


import re


# https://stackoverflow.com/a/295466/706389
def get_valid_filename(s: str) -> str:
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


# TODO deprecate and suggest to use one from my.core directly? not sure
from .utils.itertools import unique_everseen  # noqa: F401

### legacy imports, keeping them here for backwards compatibility
## hiding behind TYPE_CHECKING so it works in runtime
## in principle, warnings.deprecated decorator should cooperate with mypy, but doesn't look like it works atm?
## perhaps it doesn't work when it's used from typing_extensions

if not TYPE_CHECKING:
    from .compat import deprecated

    @deprecated('use my.core.compat.assert_never instead')
    def assert_never(*args, **kwargs):
        return compat.assert_never(*args, **kwargs)

    @deprecated('use my.core.compat.fromisoformat instead')
    def isoparse(*args, **kwargs):
        return compat.fromisoformat(*args, **kwargs)

    @deprecated('use more_itertools.one instead')
    def the(*args, **kwargs):
        import more_itertools

        return more_itertools.one(*args, **kwargs)

    @deprecated('use functools.cached_property instead')
    def cproperty(*args, **kwargs):
        import functools

        return functools.cached_property(*args, **kwargs)

    @deprecated('use more_itertools.bucket instead')
    def group_by_key(l, key):
        res = {}
        for i in l:
            kk = key(i)
            lst = res.get(kk, [])
            lst.append(i)
            res[kk] = lst
        return res

    @deprecated('use my.core.utils.itertools.make_dict instead')
    def make_dict(*args, **kwargs):
        from .utils import itertools as UI

        return UI.make_dict(*args, **kwargs)

    @deprecated('use my.core.utils.itertools.listify instead')
    def listify(*args, **kwargs):
        from .utils import itertools as UI

        return UI.listify(*args, **kwargs)

    @deprecated('use my.core.warn_if_empty instead')
    def warn_if_empty(*args, **kwargs):
        from .utils import itertools as UI

        return UI.listify(*args, **kwargs)

    @deprecated('use my.core.stat instead')
    def stat(*args, **kwargs):
        from . import stats

        return stats.stat(*args, **kwargs)

    @deprecated('use my.core.make_logger instead')
    def LazyLogger(*args, **kwargs):
        from . import logging

        return logging.LazyLogger(*args, **kwargs)

    @deprecated('use my.core.types.asdict instead')
    def asdict(*args, **kwargs):
        from . import types

        return types.asdict(*args, **kwargs)

    # todo wrap these in deprecated decorator as well?
    # TODO hmm how to deprecate these in runtime?
    # tricky cause they are actually classes/types
    from typing import Literal  # noqa: F401

    from .cachew import mcachew  # noqa: F401

    # this is kinda internal, should just use my.core.logging.setup_logger if necessary
    from .logging import setup_logger
    from .stats import Stats
    from .types import (
        Json,
        datetime_aware,
        datetime_naive,
    )

    tzdatetime = datetime_aware
else:
    from .compat import Never

    # make these invalid during type check while working in runtime
    Stats = Never
    tzdatetime = Never
    Json = Never
    datetime_naive = Never
    datetime_aware = Never
###
