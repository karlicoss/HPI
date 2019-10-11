from pathlib import Path
import functools
from typing import Union, Callable, Dict, List, Iterable, TypeVar

# some helper functions

def import_file(p: Union[str, Path], name=None):
    p = Path(p)
    if name is None:
        name = p.stem
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, p) # type: ignore
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo) # type: ignore
    return foo

def import_from(path, name):
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


# def dictify(fn=None, key=None, value=None):
#     def md(it):
#         return make_dict(it, key=key, value=value)
#     return listify(fn=fn, wrapper=md)


def setup_logger(logger, level=None, format=None, datefmt=None):
    import logging
    old_root = logging.root
    try:
        logging.root = logger
        logging.basicConfig(
            level=level or logging.DEBUG,
            format=format or '%(name)s %(asctime)s %(levelname)-8s %(filename)s:%(lineno)-4d %(message)s',
            datefmt=datefmt or '%Y-%m-%d %H:%M:%S',
        )
    finally:
        logging.root = old_root
