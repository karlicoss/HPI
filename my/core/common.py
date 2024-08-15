from glob import glob as do_glob
from pathlib import Path
from datetime import datetime
from dataclasses import is_dataclass, asdict as dataclasses_asdict
import functools
from contextlib import contextmanager
import os
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    TYPE_CHECKING,
    Tuple,
    TypeVar,
    Union,
    cast,
)
import warnings

from . import warnings as core_warnings
from . import compat
from .compat import deprecated

# some helper functions
PathIsh = Union[Path, str]

from .logging import setup_logger, LazyLogger


Paths = Union[Sequence[PathIsh], PathIsh]


DEFAULT_GLOB = '*'
def get_files(
        pp: Paths,
        glob: str=DEFAULT_GLOB,
        sort: bool=True,
        guess_compression: bool=True,
) -> Tuple[Path, ...]:
    """
    Helper function to avoid boilerplate.

    Tuple as return type is a bit friendlier for hashing/caching, so hopefully makes sense
    """
    # TODO FIXME mm, some wrapper to assert iterator isn't empty?
    sources: List[Path]
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

    paths: List[Path] = []
    for src in sources:
        if src.parts[0] == '~':
            src = src.expanduser()
        # note: glob handled first, because e.g. on Windows asterisk makes is_dir unhappy
        gs = str(src)
        if '*' in gs:
            if glob != DEFAULT_GLOB:
                warnings.warn(f"{caller()}: treating {gs} as glob path. Explicit glob={glob} argument is ignored!")
            paths.extend(map(Path, do_glob(gs)))
        elif os.path.isdir(str(src)):
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
        paths = list(sorted(paths))

    if len(paths) == 0:
        # todo make it conditionally defensive based on some global settings
        core_warnings.high(f'''
{caller()}: no paths were matched against {pp}. This might result in missing data. Likely, the directory you passed is empty.
'''.strip())
        # traceback is useful to figure out what config caused it?
        import traceback

        traceback.print_stack()

    if guess_compression:
        from .kompress import CPath, is_compressed, ZipPath

        # NOTE: wrap is just for backwards compat with vendorized kompress
        # with kompress library, only is_compressed check and Cpath should be enough
        def wrap(p: Path) -> Path:
            if isinstance(p, ZipPath):
                return p
            if p.suffix == '.zip':
                return ZipPath(p)  # type: ignore[return-value]
            if is_compressed(p):
                return CPath(p)
            return p

        paths = [wrap(p) for p in paths]
    return tuple(paths)


@functools.lru_cache(1)
def _magic():
    import magic # type: ignore
    return magic.Magic(mime=True)


# TODO could reuse in pdf module?
import mimetypes # todo do I need init()?
# todo wtf? fastermime thinks it's mime is application/json even if the extension is xz??
# whereas magic detects correctly: application/x-zstd and application/x-xz
def fastermime(path: PathIsh) -> str:
    paths = str(path)
    # mimetypes is faster
    (mime, _) = mimetypes.guess_type(paths)
    if mime is not None:
        return mime
    # magic is slower but returns more stuff
    # TODO Result type?; it's kinda racey, but perhaps better to let the caller decide?
    return _magic().from_file(paths)


Json = Dict[str, Any]


from typing import TypeVar, Callable, Generic

_R = TypeVar('_R')

# https://stackoverflow.com/a/5192374/706389
class classproperty(Generic[_R]):
    def __init__(self, f: Callable[..., _R]) -> None:
        self.f = f

    def __get__(self, obj, cls) -> _R:
        return self.f(cls)


# hmm, this doesn't really work with mypy well..
# https://github.com/python/mypy/issues/6244
# class staticproperty(Generic[_R]):
#     def __init__(self, f: Callable[[], _R]) -> None:
#         self.f = f
#
#     def __get__(self) -> _R:
#         return self.f()

# for now just serves documentation purposes... but one day might make it statically verifiable where possible?
# TODO e.g. maybe use opaque mypy alias?
datetime_naive = datetime
datetime_aware = datetime


import re
# https://stackoverflow.com/a/295466/706389
def get_valid_filename(s: str) -> str:
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


# global state that turns on/off quick stats
# can use the 'quick_stats' contextmanager
# to enable/disable this in cli so that module 'stats'
# functions don't have to implement custom 'quick' logic
QUICK_STATS = False


# in case user wants to use the stats functions/quick option
# elsewhere -- can use this decorator instead of editing
# the global state directly
@contextmanager
def quick_stats():
    global QUICK_STATS
    prev = QUICK_STATS
    try:
        QUICK_STATS = True
        yield
    finally:
        QUICK_STATS = prev


C = TypeVar('C')
Stats = Dict[str, Any]
StatsFun = Callable[[], Stats]
# todo not sure about return type...
def stat(
    func: Union[Callable[[], Iterable[C]], Iterable[C]],
    *,
    quick: bool = False,
    name: Optional[str] = None,
) -> Stats:
    if callable(func):
        fr = func()
        if hasattr(fr, '__enter__') and hasattr(fr, '__exit__'):
            # context managers has Iterable type, but they aren't data providers
            # sadly doesn't look like there is a way to tell from typing annotations
            return {}
        fname = func.__name__
    else:
        # meh. means it's just a list.. not sure how to generate a name then
        fr = func
        fname = f'unnamed_{id(fr)}'
    type_name = type(fr).__name__
    if type_name == 'DataFrame':
        # dynamic, because pandas is an optional dependency..
        df = cast(Any, fr)  # todo ugh, not sure how to annotate properly
        res = dict(
            dtypes=df.dtypes.to_dict(),
            rows=len(df),
        )
    else:
        res = _stat_iterable(fr, quick=quick)

    stat_name = name if name is not None else fname
    return {
        stat_name: res,
    }


def _stat_iterable(it: Iterable[C], quick: bool = False) -> Any:
    from more_itertools import ilen, take, first

    # todo not sure if there is something in more_itertools to compute this?
    total = 0
    errors = 0
    first_item = None
    last_item = None

    def funcit():
        nonlocal errors, first_item, last_item, total
        for x in it:
            total += 1
            if isinstance(x, Exception):
                errors += 1
            else:
                last_item = x
                if first_item is None:
                    first_item = x
            yield x

    eit = funcit()
    count: Any
    if quick or QUICK_STATS:
        initial = take(100, eit)
        count = len(initial)
        if first(eit, None) is not None: # todo can actually be none...
            # haven't exhausted
            count = f'{count}+'
    else:
        count = ilen(eit)

    res = {
        'count': count,
    }

    if total == 0:
        # not sure but I guess a good balance? wouldn't want to throw early here?
        res['warning'] = 'THE ITERABLE RETURNED NO DATA'

    if errors > 0:
        res['errors'] = errors

    def stat_item(item):
        if item is None:
            return None
        if isinstance(item, Path):
            return str(item)
        return guess_datetime(item)

    if (stat_first := stat_item(first_item)) is not None:
        res['first'] = stat_first

    if (stat_last := stat_item(last_item)) is not None:
        res['last'] = stat_last

    return res


def test_stat_iterable() -> None:
    from datetime import datetime, timedelta, timezone
    from typing import NamedTuple

    dd = datetime.fromtimestamp(123, tz=timezone.utc)
    day = timedelta(days=3)

    X = NamedTuple('X', [('x', int), ('d', datetime)])

    def it():
        yield RuntimeError('oops!')
        for i in range(2):
            yield X(x=i, d=dd + day * i)
        yield RuntimeError('bad!')
        for i in range(3):
            yield X(x=i * 10, d=dd + day * (i * 10))
        yield X(x=123, d=dd + day * 50)

    res = _stat_iterable(it())
    assert res['count']  == 1 + 2 + 1 + 3 + 1
    assert res['errors'] == 1 + 1
    assert res['last'] == dd + day * 50


# experimental, not sure about it..
def guess_datetime(x: Any) -> Optional[datetime]:
    # todo hmm implement withoutexception..
    try:
        d = asdict(x)
    except: # noqa: E722 bare except
        return None
    for k, v in d.items():
        if isinstance(v, datetime):
            return v
    return None

def test_guess_datetime() -> None:
    from datetime import datetime
    from dataclasses import dataclass
    from typing import NamedTuple

    dd = compat.fromisoformat('2021-02-01T12:34:56Z')

    # ugh.. https://github.com/python/mypy/issues/7281
    A = NamedTuple('A', [('x', int)])
    B = NamedTuple('B', [('x', int), ('created', datetime)])

    assert guess_datetime(A(x=4)) is None
    assert guess_datetime(B(x=4, created=dd)) == dd

    @dataclass
    class C:
        a: datetime
        x: int
    assert guess_datetime(C(a=dd, x=435)) == dd
    # TODO not sure what to return when multiple datetime fields?
    # TODO test @property?


def is_namedtuple(thing: Any) -> bool:
    # basic check to see if this is namedtuple-like
    _asdict = getattr(thing, '_asdict', None)
    return (_asdict is not None) and callable(_asdict)


def asdict(thing: Any) -> Json:
    # todo primitive?
    # todo exception?
    if isinstance(thing, dict):
        return thing
    if is_dataclass(thing):
        assert not isinstance(thing, type)  # to help mypy
        return dataclasses_asdict(thing)
    if is_namedtuple(thing):
        return thing._asdict()
    raise TypeError(f'Could not convert object {thing} to dict')


def assert_subpackage(name: str) -> None:
    # can lead to some unexpected issues if you 'import cachew' which being in my/core directory.. so let's protect against it
    # NOTE: if we use overlay, name can be smth like my.origg.my.core.cachew ...
    assert name == '__main__' or 'my.core' in name, f'Expected module __name__ ({name}) to be __main__ or start with my.core'


# TODO deprecate and suggest to use one from my.core directly? not sure
from .utils.itertools import unique_everseen


### legacy imports, keeping them here for backwards compatibility
## hiding behind TYPE_CHECKING so it works in runtime
## in principle, warnings.deprecated decorator should cooperate with mypy, but doesn't look like it works atm?
## perhaps it doesn't work when it's used from typing_extensions
if not TYPE_CHECKING:

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

    # todo wrap these in deprecated decorator as well?
    from .cachew import mcachew  # noqa: F401

    from typing import Literal  # noqa: F401

    # TODO hmm how to deprecate it in runtime? tricky cause it's actually a class?
    tzdatetime = datetime_aware
else:
    from .compat import Never

    tzdatetime = Never  # makes it invalid as a type while working in runtime
###
