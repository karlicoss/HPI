"""
Various helpers/transforms of iterators

Ideally this should be as small as possible and we should rely on stdlib itertools or more_itertools
"""

from __future__ import annotations

import warnings
from collections.abc import Hashable, Iterable, Iterator, Sized
from typing import (
    TYPE_CHECKING,
    Callable,
    TypeVar,
    Union,
    cast,
)

import more_itertools
from decorator import decorator

from .. import warnings as core_warnings
from ..compat import ParamSpec

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


def _identity(v: T) -> V:  # type: ignore[type-var]
    return cast(V, v)


# ugh. nothing in more_itertools?
# perhaps duplicates_everseen? but it doesn't yield non-unique elements?
def ensure_unique(it: Iterable[T], *, key: Callable[[T], K]) -> Iterable[T]:
    key2item: dict[K, T] = {}
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
    list(ensure_unique(dups, key=lambda _: object()))


def make_dict(
    it: Iterable[T],
    *,
    key: Callable[[T], K],
    # TODO make value optional instead? but then will need a typing override for it?
    value: Callable[[T], V] = _identity,
) -> dict[K, V]:
    with_keys = ((key(i), i) for i in it)
    uniques = ensure_unique(with_keys, key=lambda p: p[0])
    res: dict[K, V] = {}
    for k, i in uniques:
        res[k] = i if value is None else value(i)  # type: ignore[redundant-expr]
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
    _d2: dict[str, int] = make_dict(it, key=lambda i: str(i))
    _d3: dict[str, bool] = make_dict(it, key=lambda i: str(i), value=lambda i: i % 2 == 0)


LFP = ParamSpec('LFP')
LV = TypeVar('LV')


@decorator
def _listify(func: Callable[LFP, Iterable[LV]], *args: LFP.args, **kwargs: LFP.kwargs) -> list[LV]:
    """
    Wraps a function's return value in wrapper (e.g. list)
    Useful when an algorithm can be expressed more cleanly as a generator
    """
    return list(func(*args, **kwargs))


# ugh. decorator library has stub types, but they are way too generic?
# tried implementing my own stub, but failed -- not sure if it's possible at all?
# so seems easiest to just use specialize instantiations of decorator instead
if TYPE_CHECKING:

    def listify(func: Callable[LFP, Iterable[LV]]) -> Callable[LFP, list[LV]]: ...  # noqa: ARG001

else:
    listify = _listify


def test_listify() -> None:
    from ..compat import assert_type

    @listify
    def it() -> Iterator[int]:
        yield 1
        yield 2

    res = it()
    assert_type(res, list[int])
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
            core_warnings.medium(f"Function {func} returned empty container, make sure your config paths are correct")
        return iterable
    else:  # must be an iterator

        def wit():
            empty = True
            for i in iterable:
                yield i
                empty = False
            if empty:
                core_warnings.medium(f"Function {func} didn't emit any data, make sure your config paths are correct")

        return wit()


if TYPE_CHECKING:
    FF = TypeVar('FF', bound=Callable[..., Iterable])

    def warn_if_empty(func: FF) -> FF: ...  # noqa: ARG001

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
        assert list(res1) == ['a', 'aba']
        assert len(w) == 0

    @warn_if_empty
    def empty() -> Iterator[int]:
        yield from []

    with warnings.catch_warnings(record=True) as w:
        res2 = empty()
        assert len(w) == 0  # warning isn't emitted until iterator is consumed
        assert_type(res2, Iterator[int])
        assert list(res2) == []
        assert len(w) == 1


def test_warn_if_empty_list() -> None:
    from ..compat import assert_type

    ll = [1, 2, 3]

    @warn_if_empty
    def nonempty() -> list[int]:
        return ll

    with warnings.catch_warnings(record=True) as w:
        res1 = nonempty()
        assert len(w) == 0
        assert_type(res1, list[int])
        assert isinstance(res1, list)
        assert res1 is ll  # object should be unchanged!

    @warn_if_empty
    def empty() -> list[str]:
        return []

    with warnings.catch_warnings(record=True) as w:
        res2 = empty()
        assert len(w) == 1
        assert_type(res2, list[str])
        assert isinstance(res2, list)
        assert res2 == []


def test_warn_if_empty_unsupported() -> None:
    # these should be rejected by mypy! (will show "unused type: ignore" if we break it)
    @warn_if_empty  # type: ignore[type-var]
    def bad_return_type() -> float:
        return 0.00


_HT = TypeVar('_HT', bound=Hashable)


# NOTE: ideally we'do It = TypeVar('It', bound=Iterable[_HT]), and function would be It -> It
#       Sadly this doesn't work in mypy, doesn't look like we can have double bound TypeVar
#       Not a huge deal, since this function is for unique_eversee and
#        we need to pass iterator to unique_everseen anyway
#       TODO maybe contribute to more_itertools? https://github.com/more-itertools/more-itertools/issues/898
def check_if_hashable(iterable: Iterable[_HT]) -> Iterable[_HT]:
    """
    NOTE: Despite Hashable bound, typing annotation doesn't guarantee runtime safety
          Consider hashable type X, and Y that inherits from X, but not hashable
          Then l: list[X] = [Y(...)] is a valid expression, and type checks against Hashable,
           but isn't runtime hashable
    """
    # Sadly this doesn't work 100% correctly with dataclasses atm...
    # they all are considered hashable: https://github.com/python/mypy/issues/11463

    if isinstance(iterable, Iterator):

        def res() -> Iterator[_HT]:
            for i in iterable:
                assert isinstance(i, Hashable), i
                # ugh. need a cast due to https://github.com/python/mypy/issues/10817
                yield cast(_HT, i)

        return res()
    else:
        # hopefully, iterable that can be iterated over multiple times?
        # not sure if should have 'allowlist' of types that don't have to be transformed instead?
        for i in iterable:
            assert isinstance(i, Hashable), i
        return iterable


# TODO different policies -- error/warn/ignore?
def test_check_if_hashable() -> None:
    from dataclasses import dataclass

    import pytest

    from ..compat import assert_type

    x1: list[int] = [1, 2]
    r1 = check_if_hashable(x1)
    assert_type(r1, Iterable[int])
    assert r1 is x1

    x2: Iterator[int | str] = iter((123, 'aba'))
    r2 = check_if_hashable(x2)
    assert_type(r2, Iterable[Union[int, str]])
    assert list(r2) == [123, 'aba']

    x3: tuple[object, ...] = (789, 'aba')
    r3 = check_if_hashable(x3)
    assert_type(r3, Iterable[object])
    assert r3 is x3  # object should be unchanged

    x4: list[set[int]] = [{1, 2, 3}, {4, 5, 6}]
    with pytest.raises(Exception):
        # should be rejected by mypy sice set isn't Hashable, but also throw at runtime
        _r4 = check_if_hashable(x4)  # type: ignore[type-var]

    x5: Iterator[object] = iter([{1, 2}, {3, 4}])
    # here, we hide behind object, which is hashable
    # so mypy can't really help us anything
    r5 = check_if_hashable(x5)
    with pytest.raises(Exception):
        # note: this only throws when iterator is advanced
        list(r5)

    # dataclass is unhashable by default! unless frozen=True and eq=True, or unsafe_hash=True
    @dataclass(unsafe_hash=True)
    class X:
        a: int

    x6: list[X] = [X(a=123)]
    r6 = check_if_hashable(x6)
    assert x6 is r6

    # inherited dataclass will not be hashable!
    @dataclass
    class Y(X):
        b: str

    x7: list[Y] = [Y(a=123, b='aba')]
    with pytest.raises(Exception):
        # ideally that would also be rejected by mypy, but currently there is a bug
        # which treats all dataclasses as hashable: https://github.com/python/mypy/issues/11463
        check_if_hashable(x7)


_UET = TypeVar('_UET')
_UEU = TypeVar('_UEU')


# NOTE: for historic reasons, this function had to accept Callable that returns iterator
#        instead of just iterator
#       TODO maybe deprecated Callable support? not sure
def unique_everseen(
    fun: Callable[[], Iterable[_UET]] | Iterable[_UET],
    key: Callable[[_UET], _UEU] | None = None,
) -> Iterator[_UET]:
    import os

    if callable(fun):
        iterable = fun()
    else:
        iterable = fun

    if key is None:
        # todo check key return type as well? but it's more likely to be hashable
        if os.environ.get('HPI_CHECK_UNIQUE_EVERSEEN') is not None:
            iterable = check_if_hashable(iterable)

    return more_itertools.unique_everseen(iterable=iterable, key=key)


def test_unique_everseen() -> None:
    import pytest

    from ..tests.common import tmp_environ_set

    def fun_good() -> Iterator[int]:
        yield 123

    def fun_bad():
        return [{1, 2}, {1, 2}, {1, 3}]

    with tmp_environ_set('HPI_CHECK_UNIQUE_EVERSEEN', 'yes'):
        assert list(unique_everseen(fun_good)) == [123]

        with pytest.raises(Exception):
            # since function returns a list rather than iterator, check happens immediately
            # , even without advancing the iterator
            unique_everseen(fun_bad)

        good_list = [4, 3, 2, 1, 2, 3, 4]
        assert list(unique_everseen(good_list)) == [4, 3, 2, 1]

    with tmp_environ_set('HPI_CHECK_UNIQUE_EVERSEEN', None):
        assert list(unique_everseen(fun_bad)) == [{1, 2}, {1, 3}]
