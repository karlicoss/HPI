from __future__ import annotations

import os
import traceback
from collections.abc import Callable, Iterable, Sequence
from glob import glob as do_glob
from pathlib import Path
from typing import TYPE_CHECKING

from . import warnings

Paths = Sequence[Path | str] | Path | str


DEFAULT_GLOB = '*'


def get_files(
    pp: Paths,
    glob: str = DEFAULT_GLOB,
    *,
    sort: bool = True,
    guess_compression: bool = True,
) -> tuple[Path, ...]:
    """
    Helper function to avoid boilerplate and 'discover' files in directories.

    :param: sort: Only applies to recursive/glob file discovery.
                  Otherwise, the order specified in arguments is preserved.

    :return: Tuple of Path objects.
             Tuple instead of list is a bit friendlier for hashing/caching.
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
        # TODO ugh. very flaky... -3 because [<this function>, get_files(), <actual caller>]
        return traceback.extract_stack()[-3].filename

    paths: list[Path] = []
    for src in sources:
        if len(src.parts) > 0 and src.parts[0] == '~':
            src = src.expanduser()
        # note: glob handled first, because e.g. on Windows asterisk makes is_dir unhappy
        gs = str(src)
        if '*' in gs:  # FIXME uhhh need to test this...
            if glob != DEFAULT_GLOB:
                warnings.medium(f"{caller()}: treating {gs} as glob path. Explicit glob={glob} argument is ignored!")
            globbed = do_glob(gs)  # noqa: PTH207
            if sort:
                globbed = sorted(globbed)
            paths.extend(map(Path, globbed))
        elif os.path.isdir(str(src)):  # noqa: PTH112
            # NOTE: we're using os.path here on purpose instead of src.is_dir
            # the reason is is_dir for archives might return True and then
            # this clause would try globbing insize the archives
            # this is generally undesirable (since modules handle archives themselves)

            # todo not sure if should be recursive?
            # note: glob='**/*.ext' works without any changes.. so perhaps it's ok as it is
            gp: Iterable[Path] = src.glob(glob)
            if sort:
                gp = sorted(gp)
            paths.extend(gp)
        else:
            assert src.exists(), src
            # todo assert matches glob??
            paths.append(src)

    if len(paths) == 0:
        # todo make it conditionally defensive based on some global settings
        warnings.high(
            f'''
{caller()}: no paths were matched against {pp}. This might result in missing data. Likely, the directory you passed is empty.
'''.strip()
        )
        # traceback is useful to figure out what config caused it?
        traceback.print_stack()

    if guess_compression:
        from kompress import CPath, is_compressed

        # note: ideally we'd just wrap everything in CPath for simplicity, however
        # - it doesn't preserve original Path/str if not compressed -- perhaps should fix __new__ method
        # - currently, rb mode isn't handled correctly? https://github.com/karlicoss/kompress/issues/22
        paths = [(CPath(p) if is_compressed(p) else p) for p in paths]
    return tuple(paths)


# https://stackoverflow.com/a/5192374/706389
# NOTE: it was added to stdlib in 3.9 and then deprecated in 3.11
# seems that the suggested solution is to use custom decorator?
class classproperty[R]:
    def __init__(self, f: Callable[..., R]) -> None:
        self.f = f

    def __get__(self, obj, cls) -> R:
        return self.f(cls)


def test_classproperty() -> None:
    from typing import assert_type

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

# Legacy exports stay available at runtime but are rejected by type checkers.
if not TYPE_CHECKING:
    from .compat import deprecated

    @deprecated('use my.core.make_logger instead')
    def LazyLogger(*args, **kwargs):
        from . import logging

        return logging.LazyLogger(*args, **kwargs)

    # this is kinda internal, should just use my.core.logging.setup_logger if necessary
    from .logging import setup_logger  # noqa: F401

    @deprecated('use my.core.cachew.mcachew instead')
    def mcachew(*args, **kwargs):
        from .cachew import mcachew as _mcachew

        return _mcachew(*args, **kwargs)

    # PathIsh cannot use @deprecated because it is a union alias.
    # Resolve it here to warn on access while preserving annotations and isinstance checks.
    # Keep this hook under if not TYPE_CHECKING so type checkers still reject legacy imports.
    def __getattr__(name: str) -> object:
        if name == 'PathIsh':
            warnings.high('my.core.common.PathIsh is deprecated; use pathlib.Path | str instead', stacklevel=2)
            return Path | str
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

    # Preserve the old wildcard exports alongside named imports.
    # PathIsh is supplied by __getattr__.
    __all__ = [name for name in globals() if not name.startswith('_')] + ['PathIsh']  # noqa: F822
