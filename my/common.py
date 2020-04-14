from pathlib import Path
import functools
import types
from typing import Union, Callable, Dict, Iterable, TypeVar, Sequence, List, Optional, Any, cast

from . import init

# some helper functions
PathIsh = Union[Path, str]

# TODO port annotations to kython?..
def import_file(p: PathIsh, name: Optional[str]=None) -> types.ModuleType:
    p = Path(p)
    if name is None:
        name = p.stem
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, p)
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

def make_dict(l: Iterable[T], key: Callable[[T], K], value: Callable[[T], V]=_identity) -> Dict[K, V]:
    res: Dict[K, V] = {}
    for i in l:
        k = key(i)
        v = value(i)
        pv = res.get(k, None) # type: ignore
        if pv is not None:
            raise RuntimeError(f"Duplicate key: {k}. Previous value: {pv}, new value: {v}")
        res[k] = v
    return res


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


# TODO FIXME use in bluemaestro
# def dictify(fn=None, key=None, value=None):
#     def md(it):
#         return make_dict(it, key=key, value=value)
#     return listify(fn=fn, wrapper=md)


from .kython.klogging import setup_logger, LazyLogger


Paths = Union[Sequence[PathIsh], PathIsh]

def get_files(pp: Paths, glob: str, sort: bool=True) -> List[Path]:
    """
    Helper function to avoid boilerplate.
    """
    # TODO FIXME mm, some wrapper to assert iterator isn't empty?
    sources: List[Path] = []
    if isinstance(pp, (str, Path)):
        sources.append(Path(pp))
    else:
        sources.extend(map(Path, pp))

    paths: List[Path] = []
    for src in sources:
        if src.is_dir():
            gp: Iterable[Path] = src.glob(glob)
            paths.extend(gp)
        else:
            assert src.is_file(), src
            # TODO FIXME assert matches glob??
            paths.append(src)

    if sort:
        paths = list(sorted(paths))
    return paths


def mcachew(*args, **kwargs):
    """
    Stands for 'Maybe cachew'.
    Defensive wrapper around @cachew to make it an optional dependency.
    """
    try:
        import cachew
    except ModuleNotFoundError:
        import warnings
        warnings.warn('cachew library not found. You might want to install it to speed things up. See https://github.com/karlicoss/cachew')
        return lambda orig_func: orig_func
    else:
        import cachew.experimental
        cachew.experimental.enable_exceptions()  # TODO do it only once?
        return cachew.cachew(*args, **kwargs)


@functools.lru_cache(1)
def _magic():
    import magic # type: ignore
    return magic.Magic(mime=True)


# TODO could reuse in pdf module?
import mimetypes # TODO do I need init()?
def fastermime(path: str) -> str:
    # mimetypes is faster
    (mime, _) = mimetypes.guess_type(path)
    if mime is not None:
        return mime
    # magic is slower but returns more stuff
    # TODO FIXME Result type; it's inherently racey
    return _magic().from_file(path)


Json = Dict[str, Any]
