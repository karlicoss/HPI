from glob import glob as do_glob
from pathlib import Path
from datetime import datetime
import functools
from contextlib import contextmanager
import os
import sys
import types
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    NoReturn,
    Optional,
    Sequence,
    TYPE_CHECKING,
    Tuple,
    TypeVar,
    Union,
    cast,
    get_args,
    get_type_hints,
    get_origin,
)
import warnings
from . import warnings as core_warnings

# some helper functions
PathIsh = Union[Path, str]

# TODO only used in tests? not sure if useful at all.
def import_file(p: PathIsh, name: Optional[str] = None) -> types.ModuleType:
    p = Path(p)
    if name is None:
        name = p.stem
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, p)
    assert spec is not None, f"Fatal error; Could not create module spec from {name} {p}"
    foo = importlib.util.module_from_spec(spec)
    loader = spec.loader; assert loader is not None
    loader.exec_module(foo)
    return foo


def import_from(path: PathIsh, name: str) -> types.ModuleType:
    path = str(path)
    try:
        sys.path.append(path)
        import importlib
        return importlib.import_module(name)
    finally:
        sys.path.remove(path)


def import_dir(path: PathIsh, extra: str='') -> types.ModuleType:
    p = Path(path)
    if p.parts[0] == '~':
        p = p.expanduser() # TODO eh. not sure about this..
    return import_from(p.parent, p.name + extra)


T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# TODO deprecate? more_itertools.one should be used
def the(l: Iterable[T]) -> T:
    it = iter(l)
    try:
        first = next(it)
    except StopIteration:
        raise RuntimeError('Empty iterator?')
    assert all(e == first for e in it)
    return first


# TODO more_itertools.bucket?
def group_by_key(l: Iterable[T], key: Callable[[T], K]) -> Dict[K, List[T]]:
    res: Dict[K, List[T]] = {}
    for i in l:
        kk = key(i)
        lst = res.get(kk, [])
        lst.append(i)
        res[kk] = lst
    return res


def _identity(v: T) -> V:  # type: ignore[type-var]
    return cast(V, v)


# ugh. nothing in more_itertools?
def ensure_unique(
        it: Iterable[T],
        *,
        key: Callable[[T], K],
        value: Callable[[T], V]=_identity,
        key2value: Optional[Dict[K, V]]=None
) -> Iterable[T]:
    if key2value is None:
        key2value = {}
    for i in it:
        k = key(i)
        v = value(i)
        pv = key2value.get(k, None)
        if pv is not None:
            raise RuntimeError(f"Duplicate key: {k}. Previous value: {pv}, new value: {v}")
        key2value[k] = v
        yield i


def test_ensure_unique() -> None:
    import pytest
    assert list(ensure_unique([1, 2, 3], key=lambda i: i)) == [1, 2, 3]

    dups = [1, 2, 1, 4]
    # this works because it's lazy
    it = ensure_unique(dups, key=lambda i: i)

    # but forcing throws
    with pytest.raises(RuntimeError, match='Duplicate key'):
        list(it)

    # hacky way to force distinct objects?
    list(ensure_unique(dups, key=lambda i: object()))


def make_dict(
        it: Iterable[T],
        *,
        key: Callable[[T], K],
        value: Callable[[T], V]=_identity
) -> Dict[K, V]:
    res: Dict[K, V] = {}
    uniques = ensure_unique(it, key=key, value=value, key2value=res)
    for _ in uniques:
        pass  # force the iterator
    return res


def test_make_dict() -> None:
    it = range(5)
    d = make_dict(it, key=lambda i: i, value=lambda i: i % 2)
    assert d == {0: 0, 1: 1, 2: 0, 3: 1, 4: 0}

    # check type inference
    d2: Dict[str, int ] = make_dict(it, key=lambda i: str(i))
    d3: Dict[str, bool] = make_dict(it, key=lambda i: str(i), value=lambda i: i % 2 == 0)


# https://stackoverflow.com/a/12377059/706389
def listify(fn=None, wrapper=list):
    """
    Wraps a function's return value in wrapper (e.g. list)
    Useful when an algorithm can be expressed more cleanly as a generator
    """
    def listify_return(fn):
        @functools.wraps(fn)
        def listify_helper(*args, **kw):
            return wrapper(fn(*args, **kw))
        return listify_helper
    if fn is None:
        return listify_return
    return listify_return(fn)


# todo use in bluemaestro
# def dictify(fn=None, key=None, value=None):
#     def md(it):
#         return make_dict(it, key=key, value=value)
#     return listify(fn=fn, wrapper=md)


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

_C = TypeVar('_C')
_R = TypeVar('_R')

# https://stackoverflow.com/a/5192374/706389
class classproperty(Generic[_R]):
    def __init__(self, f: Callable[[_C], _R]) -> None:
        self.f = f

    def __get__(self, obj: None, cls: _C) -> _R:
        return self.f(cls)


# hmm, this doesn't really work with mypy well..
# https://github.com/python/mypy/issues/6244
# class staticproperty(Generic[_R]):
#     def __init__(self, f: Callable[[], _R]) -> None:
#         self.f = f
#
#     def __get__(self) -> _R:
#         return self.f()

# TODO deprecate in favor of datetime_aware
tzdatetime = datetime


# TODO doctests?
def isoparse(s: str) -> tzdatetime:
    """
    Parses timestamps formatted like 2020-05-01T10:32:02.925961Z
    """
    # TODO could use dateutil? but it's quite slow as far as I remember..
    # TODO support non-utc.. somehow?
    assert s.endswith('Z'), s
    s = s[:-1] + '+00:00'
    return datetime.fromisoformat(s)


import re
# https://stackoverflow.com/a/295466/706389
def get_valid_filename(s: str) -> str:
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


from typing import Generic, Sized, Callable


# X = TypeVar('X')
def _warn_iterator(it, f: Any=None):
    emitted = False
    for i in it:
        yield i
        emitted = True
    if not emitted:
        warnings.warn(f"Function {f} didn't emit any data, make sure your config paths are correct")


# TODO ugh, so I want to express something like:
# X = TypeVar('X')
# C = TypeVar('C', bound=Iterable[X])
# _warn_iterable(it: C) -> C
# but apparently I can't??? ugh.
# https://github.com/python/typing/issues/548
# I guess for now overloads are fine...

from typing import overload
X = TypeVar('X')
@overload
def _warn_iterable(it: List[X]    , f: Any=None) -> List[X]    : ...
@overload
def _warn_iterable(it: Iterable[X], f: Any=None) -> Iterable[X]: ...
def _warn_iterable(it, f=None):
    if isinstance(it, Sized):
        sz = len(it)
        if sz == 0:
            warnings.warn(f"Function {f} returned empty container, make sure your config paths are correct")
        return it
    else:
        return _warn_iterator(it, f=f)


# ok, this seems to work...
# https://github.com/python/mypy/issues/1927#issue-167100413
FL = TypeVar('FL', bound=Callable[..., List])
FI = TypeVar('FI', bound=Callable[..., Iterable])

@overload
def warn_if_empty(f: FL) -> FL: ...
@overload
def warn_if_empty(f: FI) -> FI: ...


def warn_if_empty(f):
    from functools import wraps

    @wraps(f)
    def wrapped(*args, **kwargs):
        res = f(*args, **kwargs)
        return _warn_iterable(res, f=f)
    return wrapped


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
    from datetime import datetime, timedelta
    from typing import NamedTuple

    dd = datetime.utcfromtimestamp(123)
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

    dd = isoparse('2021-02-01T12:34:56Z')

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
    import dataclasses as D
    if D.is_dataclass(thing):
        return D.asdict(thing)
    if is_namedtuple(thing):
        return thing._asdict()
    raise TypeError(f'Could not convert object {thing} to dict')


# for now just serves documentation purposes... but one day might make it statically verifiable where possible?
# TODO e.g. maybe use opaque mypy alias?
datetime_naive = datetime
datetime_aware = datetime


def assert_subpackage(name: str) -> None:
    # can lead to some unexpected issues if you 'import cachew' which being in my/core directory.. so let's protect against it
    # NOTE: if we use overlay, name can be smth like my.origg.my.core.cachew ...
    assert name == '__main__' or 'my.core' in name, f'Expected module __name__ ({name}) to be __main__ or start with my.core'


from .compat import ParamSpec
_P = ParamSpec('_P')
_T = TypeVar('_T')

# https://stackoverflow.com/a/10436851/706389
from concurrent.futures import Future, Executor
class DummyExecutor(Executor):
    def __init__(self, max_workers: Optional[int]=1) -> None:
        self._shutdown = False
        self._max_workers = max_workers

    if TYPE_CHECKING:
        if sys.version_info[:2] <= (3, 8):
            # 3.8 doesn't support ParamSpec as Callable arg :(
            # and any attempt to type results in incompatible supertype.. so whatever
            def submit(self, fn, *args, **kwargs): ...
        else:
            def submit(self, fn: Callable[_P, _T], /, *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]: ...
    else:
        def submit(self, fn, *args, **kwargs):
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            f: Future[Any] = Future()
            try:
                result = fn(*args, **kwargs)
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                f.set_exception(e)
            else:
                f.set_result(result)

            return f

    def shutdown(self, wait: bool=True, **kwargs) -> None:
        self._shutdown = True


# see https://hakibenita.com/python-mypy-exhaustive-checking#exhaustiveness-checking
def assert_never(value: NoReturn) -> NoReturn:
    assert False, f'Unhandled value: {value} ({type(value).__name__})'


def _check_all_hashable(fun):
    # TODO ok, take callable?
    hints = get_type_hints(fun)
    # TODO needs to be defensive like in cachew?
    return_type = hints.get('return')
    # TODO check if None
    origin = get_origin(return_type)  # Iterator etc?
    (arg,) = get_args(return_type)
    # options we wanna handle are simple type on the top level or union
    arg_origin = get_origin(arg)

    if sys.version_info[:2] >= (3, 10):
        is_uniontype = arg_origin is types.UnionType
    else:
        is_uniontype = False

    is_union = arg_origin is Union or is_uniontype
    if is_union:
        to_check = get_args(arg)
    else:
        to_check = (arg,)

    no_hash = [
        t
        for t in to_check
        # seems that objects that have not overridden hash have the attribute but it's set to None
        if getattr(t, '__hash__', None) is None
    ]
    assert len(no_hash) == 0, f'Types {no_hash} are not hashable, this will result in significant performance downgrade for unique_everseen'


_UET = TypeVar('_UET')
_UEU = TypeVar('_UEU')


def unique_everseen(
    fun: Callable[[], Iterable[_UET]],
    key: Optional[Callable[[_UET], _UEU]] = None,
) -> Iterator[_UET]:
    # TODO support normal iterable as well?
    import more_itertools

    # NOTE: it has to take original callable, because otherwise we don't have access to generator type annotations
    iterable = fun()

    if key is None:
        # todo check key return type as well? but it's more likely to be hashable
        if os.environ.get('HPI_CHECK_UNIQUE_EVERSEEN') is not None:
            _check_all_hashable(fun)

    return more_itertools.unique_everseen(iterable=iterable, key=key)


## legacy imports, keeping them here for backwards compatibility
from functools import cached_property as cproperty
from typing import Literal
from .cachew import mcachew
##
