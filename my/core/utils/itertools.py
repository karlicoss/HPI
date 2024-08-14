"""
Various helpers/transforms of iterators

Ideally this should be as small as possible and we should rely on stdlib itertools or more_itertools
"""

from typing import Callable, Dict, Iterable, Iterator, Sized, TypeVar, List, cast, TYPE_CHECKING
import warnings

from ..compat import ParamSpec

from decorator import decorator

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


def _identity(v: T) -> V:  # type: ignore[type-var]
    return cast(V, v)


# ugh. nothing in more_itertools?
# perhaps duplicates_everseen? but it doesn't yield non-unique elements?
def ensure_unique(it: Iterable[T], *, key: Callable[[T], K]) -> Iterable[T]:
    key2item: Dict[K, T] = {}
    for i in it:
        k = key(i)
        pi = key2item.get(k, None)
        if pi is not None:
            raise RuntimeError(f"Duplicate key: {k}. Previous value: {pi}, new value: {i}")
        key2item[k] = i
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
    # TODO make value optional instead? but then will need a typing override for it?
    value: Callable[[T], V] = _identity,
) -> Dict[K, V]:
    with_keys = ((key(i), i) for i in it)
    uniques = ensure_unique(with_keys, key=lambda p: p[0])
    res: Dict[K, V] = {}
    for k, i in uniques:
        res[k] = i if value is None else value(i)
    return res


def test_make_dict() -> None:
    import pytest

    it = range(5)
    d = make_dict(it, key=lambda i: i, value=lambda i: i % 2)
    assert d == {0: 0, 1: 1, 2: 0, 3: 1, 4: 0}

    it = range(5)
    with pytest.raises(RuntimeError, match='Duplicate key'):
        d = make_dict(it, key=lambda i: i % 2, value=lambda i: i)

    # check type inference
    d2: Dict[str, int] = make_dict(it, key=lambda i: str(i))
    d3: Dict[str, bool] = make_dict(it, key=lambda i: str(i), value=lambda i: i % 2 == 0)


LFP = ParamSpec('LFP')
LV = TypeVar('LV')


@decorator
def _listify(func: Callable[LFP, Iterable[LV]], *args: LFP.args, **kwargs: LFP.kwargs) -> List[LV]:
    """
    Wraps a function's return value in wrapper (e.g. list)
    Useful when an algorithm can be expressed more cleanly as a generator
    """
    return list(func(*args, **kwargs))


# ugh. decorator library has stub types, but they are way too generic?
# tried implementing my own stub, but failed -- not sure if it's possible at all?
# so seems easiest to just use specialize instantiations of decorator instead
if TYPE_CHECKING:

    def listify(func: Callable[LFP, Iterable[LV]]) -> Callable[LFP, List[LV]]: ...

else:
    listify = _listify


def test_listify() -> None:
    from ..compat import assert_type

    @listify
    def it() -> Iterator[int]:
        yield 1
        yield 2

    res = it()
    assert_type(res, List[int])
    assert res == [1, 2]


@decorator
def _warn_if_empty(func, *args, **kwargs):
    # so there is a more_itertools.peekable which could work nicely for these purposes
    # the downside is that it would start advancing the generator right after it's created
    # , which can be somewhat confusing
    iterable = func(*args, **kwargs)

    if isinstance(iterable, Sized):
        sz = len(iterable)
        if sz == 0:
            # todo use hpi warnings here?
            warnings.warn(f"Function {func} returned empty container, make sure your config paths are correct")
        return iterable
    else:  # must be an iterator

        def wit():
            empty = True
            for i in iterable:
                yield i
                empty = False
            if empty:
                warnings.warn(f"Function {func} didn't emit any data, make sure your config paths are correct")

        return wit()


if TYPE_CHECKING:
    FF = TypeVar('FF', bound=Callable[..., Iterable])

    def warn_if_empty(f: FF) -> FF: ...

else:
    warn_if_empty = _warn_if_empty


def test_warn_if_empty_iterator() -> None:
    from ..compat import assert_type

    @warn_if_empty
    def nonempty() -> Iterator[str]:
        yield 'a'
        yield 'aba'

    with warnings.catch_warnings(record=True) as w:
        res1 = nonempty()
        assert len(w) == 0  # warning isn't emitted until iterator is consumed
        assert_type(res1, Iterator[str])
        # assert isinstance(res1, generator)  # FIXME ??? how
        assert list(res1) == ['a', 'aba']
        assert len(w) == 0

    @warn_if_empty
    def empty() -> Iterator[int]:
        yield from []

    with warnings.catch_warnings(record=True) as w:
        res2 = empty()
        assert len(w) == 0  # warning isn't emitted until iterator is consumed
        assert_type(res2, Iterator[int])
        # assert isinstance(res1, generator)  # FIXME ??? how
        assert list(res2) == []
        assert len(w) == 1


def test_warn_if_empty_list() -> None:
    from ..compat import assert_type

    ll = [1, 2, 3]

    @warn_if_empty
    def nonempty() -> List[int]:
        return ll


    with warnings.catch_warnings(record=True) as w:
        res1 = nonempty()
        assert len(w) == 0
        assert_type(res1, List[int])
        assert isinstance(res1, list)
        assert res1 is ll  # object should be unchanged!


    @warn_if_empty
    def empty() -> List[str]:
        return []


    with warnings.catch_warnings(record=True) as w:
        res2 = empty()
        assert len(w) == 1
        assert_type(res2, List[str])
        assert isinstance(res2, list)
        assert res2 == []


def test_warn_if_empty_unsupported() -> None:
    # these should be rejected by mypy! (will show "unused type: ignore" if we break it)
    @warn_if_empty  # type: ignore[type-var]
    def bad_return_type() -> float:
        return 0.00
