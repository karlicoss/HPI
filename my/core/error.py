"""
Various error handling helpers
See https://beepb00p.xyz/mypy-error-handling.html#kiss for more detail
"""

from itertools import tee
from typing import Union, TypeVar, Iterable, List, Tuple, Type


T = TypeVar('T')
E = TypeVar('E', bound=Exception) # TODO make covariant?

ResT = Union[T, E]

Res = ResT[T, Exception]


def unwrap(res: Res[T]) -> T:
    if isinstance(res, Exception):
        raise res
    else:
        return res


def echain(ex: E, cause: Exception) -> E:
    ex.__cause__ = cause
    return ex


def split_errors(l: Iterable[ResT[T, E]], ET: Type[E]) -> Tuple[Iterable[T], Iterable[E]]:
    # TODO would be nice to have ET=Exception default?
    vit, eit = tee(l)
    # TODO ugh, not sure if I can reconcile type checking and runtime and convince mypy that ET and E are the same type?
    values: Iterable[T] = (
        r # type: ignore[misc]
        for r in vit
        if not isinstance(r, ET))
    errors: Iterable[E] = (
        r
        for r in eit
        if     isinstance(r, ET))
    # TODO would be interesting to be able to have yield statement anywehere in code
    # so there are multiple 'entry points' to the return value
    return (values, errors)


def sort_res_by(items: Iterable[ResT], key) -> List[ResT]:
    """
    The general idea is: just alaways carry errors with the entry that precedes them
    """
    # TODO ResT object should hold exception class?...
    group = []
    groups = []
    for i in items:
        if isinstance(i, Exception):
            group.append(i)
        else:
            groups.append((i, group))
            group = []

    results = []
    for v, errs in sorted(groups, key=lambda p: key(p[0])):
        results.extend(errs)
        results.append(v)
    results.extend(group)

    return results


def test_sort_res_by() -> None:
    class Exc(Exception):
        def __eq__(self, other):
            return self.args == other.args

    ress = [
        Exc('first'),
        Exc('second'),
        5,
        3,
        Exc('xxx'),
        2,
        1,
        Exc('last'),
    ]
    results = sort_res_by(ress, lambda x: x) # type: ignore
    assert results == [
        1,
        Exc('xxx'),
        2,
        3,
        Exc('first'),
        Exc('second'),
        5,
        Exc('last'),
    ]

    results2 = sort_res_by(ress + [0], lambda x: x) # type: ignore
    assert results2 == [Exc('last'), 0] + results[:-1]

