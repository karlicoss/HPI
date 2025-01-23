'''
Helpers for hpi doctor/stats functionality.
'''

from __future__ import annotations

import collections.abc
import importlib
import inspect
import typing
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import (
    Any,
    Callable,
    Protocol,
    cast,
)

from .types import asdict

Stats = dict[str, Any]


class StatsFun(Protocol):
    def __call__(self, *, quick: bool = False) -> Stats: ...


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


def stat(
    func: Callable[[], Iterable[Any]] | Iterable[Any],
    *,
    quick: bool = False,
    name: str | None = None,
) -> Stats:
    """
    Extracts various statistics from a passed iterable/callable, e.g.:
    - number of items
    - first/last item
    - timestamps associated with first/last item

    If quick is set, then only first 100 items of the iterable will be processed
    """
    if callable(func):
        fr = func()
        if hasattr(fr, '__enter__') and hasattr(fr, '__exit__'):
            # context managers has Iterable type, but they aren't data providers
            #  sadly doesn't look like there is a way to tell from typing annotations
            # Ideally we'd detect this in is_data_provider...
            #  but there is no way of knowing without actually calling it first :(
            return {}
        fname = func.__name__
    else:
        # meh. means it's just a list.. not sure how to generate a name then
        fr = func
        fname = f'unnamed_{id(fr)}'
    type_name = type(fr).__name__
    extras = {}
    if type_name == 'DataFrame':
        # dynamic, because pandas is an optional dependency..
        df = cast(Any, fr)  # todo ugh, not sure how to annotate properly
        df = df.reset_index()

        fr = df.to_dict(orient='records')

        dtypes = df.dtypes.to_dict()
        extras['dtypes'] = dtypes

    res = _stat_iterable(fr, quick=quick)
    res.update(extras)

    stat_name = name if name is not None else fname
    return {
        stat_name: res,
    }


def test_stat() -> None:
    # the bulk of testing is in test_stat_iterable

    # works with 'anonymous' lists
    res = stat([1, 2, 3])
    [(name, v)] = res.items()
    # note: name will be a little funny since anonymous list doesn't have one
    assert v == {'count': 3}
    #

    # works with functions:
    def fun():
        return [4, 5, 6]

    assert stat(fun) == {'fun': {'count': 3}}
    #

    # context managers are technically iterable
    #  , but usually we wouldn't want to compute stats for them
    # this is mainly intended for guess_stats,
    #  since it can't tell whether the function is a ctx manager without calling it
    @contextmanager
    def cm():
        yield 1
        yield 3

    assert stat(cm) == {}  # type: ignore[arg-type]
    #

    # works with pandas dataframes
    import numpy as np
    import pandas as pd

    def df() -> pd.DataFrame:
        dates = pd.date_range(start='2024-02-10 08:00', end='2024-02-11 16:00', freq='5h')
        return pd.DataFrame([f'value{i}' for i, _ in enumerate(dates)], index=dates, columns=['value'])

    assert stat(df) == {
        'df': {
            'count': 7,
            'dtypes': {
                'index': np.dtype('<M8[ns]'),
                'value': np.dtype('O'),
            },
            'first': pd.Timestamp('2024-02-10 08:00'),
            'last': pd.Timestamp('2024-02-11 14:00'),
        },
    }
    #


def get_stats(module_name: str, *, guess: bool = False) -> StatsFun | None:
    stats: StatsFun | None = None
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return None
    stats = getattr(module, 'stats', None)
    if stats is None:
        stats = guess_stats(module)
    return stats


# TODO maybe could be enough to annotate OUTPUTS or something like that?
# then stats could just use them as hints?
def guess_stats(module: ModuleType) -> StatsFun | None:
    """
    If the module doesn't have explicitly defined 'stat' function,
     this is used to try to guess what could be included in stats automatically
    """
    providers = _guess_data_providers(module)
    if len(providers) == 0:
        return None

    def auto_stats(*, quick: bool = False) -> Stats:
        res = {}
        for k, v in providers.items():
            res.update(stat(v, quick=quick, name=k))
        return res

    return auto_stats


def test_guess_stats() -> None:
    import my.core.tests.auto_stats as M

    auto_stats = guess_stats(M)
    assert auto_stats is not None
    res = auto_stats(quick=False)

    assert res == {
        'inputs': {
            'count': 3,
            'first': 'file1.json',
            'last': 'file3.json',
        },
        'iter_data': {
            'count': 9,
            'first': datetime(2020, 1, 1, 1, 1, 1),
            'last': datetime(2020, 1, 3, 1, 1, 1),
        },
    }


def _guess_data_providers(module: ModuleType) -> dict[str, Callable]:
    mfunctions = inspect.getmembers(module, inspect.isfunction)
    return {k: v for k, v in mfunctions if is_data_provider(v)}


# todo how to exclude deprecated data providers?
def is_data_provider(fun: Any) -> bool:
    """
    Criteria for being a "data provider":
    1. returns iterable or something like that
    2. takes no arguments? (otherwise not callable by stats anyway?)
    3. doesn't start with an underscore (those are probably helper functions?)
    """
    # todo maybe for 2 allow default arguments? not sure
    # one example which could benefit is my.pdfs
    if fun is None:
        return False
    # todo. uh.. very similar to what cachew is trying to do?
    try:
        sig = inspect.signature(fun)
    except (ValueError, TypeError):  # not a function?
        return False

    # has at least one argument without default values
    if len(list(_sig_required_params(sig))) > 0:
        return False

    if hasattr(fun, '__name__'):
        # probably a helper function?
        if fun.__name__.startswith('_'):
            return False

    # inspect.signature might return str instead of a proper type object
    # if from __future__ import annotations is used
    # so best to rely on get_type_hints (which evals the annotations)
    type_hints = typing.get_type_hints(fun)
    return_type = type_hints.get('return')
    if return_type is None:
        return False

    return _type_is_iterable(return_type)


def test_is_data_provider() -> None:
    idp = is_data_provider
    assert not idp(None)
    assert not idp(int)
    assert not idp("x")

    def no_return_type():
        return [1, 2, 3]

    assert not idp(no_return_type)

    lam = lambda: [1, 2]
    assert not idp(lam)

    def has_extra_args(count) -> list[int]:
        return list(range(count))

    assert not idp(has_extra_args)

    def has_return_type() -> Sequence[str]:
        return ['a', 'b', 'c']

    assert idp(has_return_type)

    def _helper_func() -> Iterator[Any]:
        yield 1

    assert not idp(_helper_func)

    def inputs() -> Iterator[Any]:
        yield 1

    assert idp(inputs)

    def producer_inputs() -> Iterator[Any]:
        yield 1

    assert idp(producer_inputs)


def _sig_required_params(sig: inspect.Signature) -> Iterator[inspect.Parameter]:
    """
    Returns parameters the user is required to provide - e.g. ones that don't have default values
    """
    for param in sig.parameters.values():
        if param.default == inspect.Parameter.empty:
            yield param


def test_sig_required_params() -> None:

    def x() -> int:
        return 5

    assert len(list(_sig_required_params(inspect.signature(x)))) == 0

    def y(arg: int) -> int:
        return arg

    assert len(list(_sig_required_params(inspect.signature(y)))) == 1

    # from stats perspective, this should be treated as a data provider as well
    # could be that the default value to the data provider is the 'default'
    # path to use for inputs/a function to provide input data
    def z(arg: int = 5) -> int:
        return arg

    assert len(list(_sig_required_params(inspect.signature(z)))) == 0


def _type_is_iterable(type_spec) -> bool:
    origin = typing.get_origin(type_spec)
    if origin is None:
        return False

    # explicitly exclude dicts... not sure?
    if issubclass(origin, collections.abc.Mapping):
        return False

    if issubclass(origin, collections.abc.Iterable):
        return True

    return False


# todo docstring test?
def test_type_is_iterable() -> None:
    fun = _type_is_iterable
    assert not fun(None)
    assert not fun(int)
    assert not fun(Any)
    assert not fun(dict[int, int])

    assert fun(list[int])
    assert fun(Sequence[dict[str, str]])
    assert fun(Iterable[Any])


def _stat_item(item):
    if item is None:
        return None
    if isinstance(item, Path):
        return str(item)
    return _guess_datetime(item)


def _stat_iterable(it: Iterable[Any], *, quick: bool = False) -> Stats:
    from more_itertools import first, ilen, take

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
        if first(eit, None) is not None:  # todo can actually be none...
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

    if (stat_first := _stat_item(first_item)) is not None:
        res['first'] = stat_first

    if (stat_last := _stat_item(last_item)) is not None:
        res['last'] = stat_last

    return res


def test_stat_iterable() -> None:
    from datetime import datetime, timedelta, timezone
    from typing import NamedTuple

    dd = datetime.fromtimestamp(123, tz=timezone.utc)
    day = timedelta(days=3)

    class X(NamedTuple):
        x: int
        d: datetime

    def it():
        yield RuntimeError('oops!')
        for i in range(2):
            yield X(x=i, d=dd + day * i)
        yield RuntimeError('bad!')
        for i in range(3):
            yield X(x=i * 10, d=dd + day * (i * 10))
        yield X(x=123, d=dd + day * 50)

    res = _stat_iterable(it())
    assert res['count'] == 1 + 2 + 1 + 3 + 1
    assert res['errors'] == 1 + 1
    assert res['last'] == dd + day * 50


# experimental, not sure about it..
def _guess_datetime(x: Any) -> datetime | None:
    # todo hmm implement without exception..
    try:
        d = asdict(x)
    except:  # noqa: E722 bare except
        return None
    for v in d.values():
        if isinstance(v, datetime):
            return v
    return None


def test_guess_datetime() -> None:
    from dataclasses import dataclass
    from typing import NamedTuple

    from .compat import fromisoformat

    dd = fromisoformat('2021-02-01T12:34:56Z')

    class A(NamedTuple):
        x: int

    class B(NamedTuple):
        x: int
        created: datetime

    assert _guess_datetime(A(x=4)) is None
    assert _guess_datetime(B(x=4, created=dd)) == dd

    @dataclass
    class C:
        a: datetime
        x: int

    assert _guess_datetime(C(a=dd, x=435)) == dd
    # TODO not sure what to return when multiple datetime fields?
    # TODO test @property?
