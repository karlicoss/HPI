from glob import glob as do_glob
from pathlib import Path
from datetime import datetime
import functools
import types
from typing import Union, Callable, Dict, Iterable, TypeVar, Sequence, List, Optional, Any, cast, Tuple, TYPE_CHECKING
import warnings
from . import warnings as core_warnings

# some helper functions
PathIsh = Union[Path, str]

# TODO only used in tests? not sure if useful at all.
# TODO port annotations to kython?..
def import_file(p: PathIsh, name: Optional[str]=None) -> types.ModuleType:
    p = Path(p)
    if name is None:
        name = p.stem
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, p)
    assert spec is not None, f"Fatal error; Could not create module spec from {name} {p}"
    foo = importlib.util.module_from_spec(spec)
    loader = spec.loader; assert loader is not None
    loader.exec_module(foo) # type: ignore[attr-defined]
    return foo


def import_from(path: PathIsh, name: str) -> types.ModuleType:
    path = str(path)
    import sys
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

def the(l: Iterable[T]) -> T:
    it = iter(l)
    try:
        first = next(it)
    except StopIteration as ee:
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


def _identity(v: T) -> V:
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
        pv = key2value.get(k, None)  # type: ignore
        if pv is not None:
            raise RuntimeError(f"Duplicate key: {k}. Previous value: {pv}, new value: {v}")
        key2value[k] = v
        yield i


def test_ensure_unique() -> None:
    import pytest  # type: ignore
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


Cl = TypeVar('Cl')
R = TypeVar('R')

def cproperty(f: Callable[[Cl], R]) -> R:
    return property(functools.lru_cache(maxsize=1)(f)) # type: ignore


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
            return () # early return to prevent warnings etc
        sources = [Path(pp)]
    else:
        sources = [Path(p) for p in pp]

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
        elif src.is_dir():
            # todo not sure if should be recursive?
            # note: glob='**/*.ext' works without any changes.. so perhaps it's ok as it is
            gp: Iterable[Path] = src.glob(glob)
            paths.extend(gp)
        else:
            if not src.is_file():
                # todo not sure, might be race condition?
                raise RuntimeError(f"Expected '{src}' to exist")
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
        from .kompress import CPath, is_compressed
        paths = [CPath(p) if is_compressed(p) else p for p in paths]
    return tuple(paths)


# TODO annotate it, perhaps use 'dependent' type (for @doublewrap stuff)
if TYPE_CHECKING:
    from typing import Callable, TypeVar
    from typing_extensions import Protocol
    # TODO reuse types from cachew? although not sure if we want hard dependency on it in typecheck time..
    # I guess, later just define pass through once this is fixed: https://github.com/python/typing/issues/270
    # ok, that's actually a super nice 'pattern'
    F = TypeVar('F')
    class McachewType(Protocol):
        def __call__(
                self,
                cache_path: Any=None,
                *,
                hashf: Any=None, # todo deprecate
                depends_on: Any=None,
                force_file: bool=False,
                chunk_by: int=0,
                logger: Any=None,
        ) -> Callable[[F], F]:
            ...

    mcachew: McachewType


_CACHE_DIR_NONE_HACK = Path('/tmp/hpi/cachew_none_hack')
"""See core.cachew.cache_dir for the explanation"""


_cache_path_dflt = cast(str, object())
# TODO I don't really like 'mcachew', just 'cache' would be better... maybe?
# todo ugh. I think it needs @doublewrap, otherwise @mcachew without args doesn't work
# but it's a bit problematic.. doublewrap works by defecting if the first arg is callable
# but here cache_path can also be a callable (for lazy/dynamic path)... so unclear how to detect this
def mcachew(cache_path=_cache_path_dflt, **kwargs): # type: ignore[no-redef]
    """
    Stands for 'Maybe cachew'.
    Defensive wrapper around @cachew to make it an optional dependency.
    """
    if cache_path is _cache_path_dflt:
        # wasn't specified... so we need to use cache_dir
        from .cachew import cache_dir
        cache_path = cache_dir()

    if isinstance(cache_path, (str, Path)):
        try:
            # check that it starts with 'hack' path
            Path(cache_path).relative_to(_CACHE_DIR_NONE_HACK)
        except:
            pass # no action needed, doesn't start with 'hack' string
        else:
            # todo show warning? tbh unclear how to detect when user stopped using 'old' way and using suffix instead?
            # if it does, means that user wanted to disable cache
            cache_path = None
    try:
        import cachew
    except ModuleNotFoundError:
        warnings.warn('cachew library not found. You might want to install it to speed things up. See https://github.com/karlicoss/cachew')
        return lambda orig_func: orig_func
    else:
        kwargs['cache_path'] = cache_path
        return cachew.cachew(**kwargs)


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

# for now just serves documentation purposes... but one day might make it statically verifiable where possible?
# TODO e.g. maybe use opaque mypy alias?
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

from .compat import Literal


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
    return wrapped # type: ignore


# hacky hook to speed up for 'hpi doctor'
# todo think about something better
QUICK_STATS = False


C = TypeVar('C')
Stats = Dict[str, Any]
StatsFun = Callable[[], Stats]
# todo not sure about return type...
def stat(func: Union[Callable[[], Iterable[C]], Iterable[C]]) -> Stats:
    if callable(func):
        fr = func()
        fname = func.__name__
    else:
        # meh. means it's just a list.. not sure how to generate a name then
        fr = func
        fname = f'unnamed_{id(fr)}'
    tname = type(fr).__name__
    if tname == 'DataFrame':
        # dynamic, because pandas is an optional dependency..
        df = cast(Any, fr) # todo ugh, not sure how to annotate properly
        res = dict(
            dtypes=df.dtypes.to_dict(),
            rows=len(df),
        )
    else:
        res = _stat_iterable(fr)
    return {
        fname: res,
    }


def _stat_iterable(it: Iterable[C]) -> Any:
    from more_itertools import ilen, take, first

    # todo not sure if there is something in more_itertools to compute this?
    total = 0
    errors = 0
    last = None
    def funcit():
        nonlocal errors, last, total
        for x in it:
            total += 1
            if isinstance(x, Exception):
                errors += 1
            else:
                last = x
            yield x

    eit = funcit()
    count: Any
    if QUICK_STATS:
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

    if last is not None:
        dt = guess_datetime(last)
        if dt is not None:
            res['last'] = dt
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
    except:
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




datetime_naive = datetime
datetime_aware = datetime


def assert_subpackage(name: str) -> None:
    # can lead to some unexpected issues if you 'import cachew' which being in my/core directory.. so let's protect against it
    # NOTE: if we use overlay, name can be smth like my.origg.my.core.cachew ...
    assert name == '__main__' or 'my.core' in name, f'Expected module __name__ ({name}) to be __main__ or start with my.core'


# https://stackoverflow.com/a/10436851/706389
from concurrent.futures import Future, Executor
class DummyExecutor(Executor):
    def __init__(self, max_workers: Optional[int]=1) -> None:
        self._shutdown = False
        self._max_workers = max_workers

    # TODO: once support for 3.7 is dropped,
    # can make 'fn' a positional only parameter,
    # which fixes the mypy error this throws without the type: ignore
    def submit(self, fn, *args, **kwargs) -> Future:  # type: ignore[override]
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

    def shutdown(self, wait: bool=True) -> None:  # type: ignore[override]
        self._shutdown = True
