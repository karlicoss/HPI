"""
Various error handling helpers
See https://beepb00p.xyz/mypy-error-handling.html#kiss for more detail
"""

from itertools import tee
from typing import Union, TypeVar, Iterable, List, Tuple, Type, Optional, Callable, Any


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
    # TODO would be nice to have ET=Exception default? but it causes some mypy complaints?
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


def sort_res_by(items: Iterable[Res[T]], key: Callable[[T], Any]) -> List[Res[T]]:
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

    results: List[Res[T]] = []
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



# helpers to associate timestamps with the errors (so something meaningful could be displayed on the plots, for example)
# todo document it under 'patterns' somewhere...

# todo proper typevar?
from datetime import datetime
def set_error_datetime(e: Exception, dt: datetime) -> None:
    # at the moment, we're using isoformat() instead of datetime directly to make it cachew-friendly
    # once cachew preserves exception argument types, we can remove these hacks
    e.args = e.args + (dt.isoformat(), )
    # todo not sure if should return new exception?


def extract_error_datetime(e: Exception) -> Optional[datetime]:
    from .common import fromisoformat
    import re
    # TODO FIXME meh. definitely need to preserve exception args types in cachew if possible..
    for x in reversed(e.args):
        m = re.search(r'\d{4}-\d\d-\d\d(T..:..:..)?(\.\d{6})?(\+.....)?', x)
        if m is None:
            continue
        ss = m.group(0)
        # todo not sure if should be defensive??
        return fromisoformat(ss)
    return None


def test_datetime_errors() -> None:
    import pytz
    dt_notz = datetime.now()
    dt_tz   = datetime.now(tz=pytz.timezone('Europe/Amsterdam'))
    for dt in [dt_tz, dt_notz]:
        e1 = RuntimeError('whatever')
        assert extract_error_datetime(e1) is None
        set_error_datetime(e1, dt=dt)
        assert extract_error_datetime(e1) == dt
        # test that cachew can handle it...
        e2 = RuntimeError(str(e1.args))
        assert extract_error_datetime(e2) == dt


    e3 = RuntimeError(str(['one', '2019-11-27T08:56:00', 'three']))
    assert extract_error_datetime(e3) is not None

    # date only
    e4 = RuntimeError(str(['one', '2019-11-27', 'three']))
    assert extract_error_datetime(e4) is not None
