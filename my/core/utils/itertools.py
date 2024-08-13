"""
Various helpers/transforms of iterators

Ideally this should be as small as possible and we should rely on stdlib itertools or more_itertools
"""

from typing import Callable, Dict, Iterable, TypeVar, cast


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
