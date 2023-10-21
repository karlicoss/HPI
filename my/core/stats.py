'''
Helpers for hpi doctor/stats functionality.
'''
import collections
import importlib
import inspect
import typing
from typing import Optional, Callable, Any, Iterator, Sequence, Dict, List

from .common import StatsFun, Stats, stat


# TODO maybe could be enough to annotate OUTPUTS or something like that?
# then stats could just use them as hints?
def guess_stats(module_name: str, quick: bool = False) -> Optional[StatsFun]:
    providers = guess_data_providers(module_name)
    if len(providers) == 0:
        return None

    def auto_stats() -> Stats:
        res = {}
        for k, v in providers.items():
            res.update(stat(v, quick=quick, name=k))
        return res

    return auto_stats


def test_guess_stats() -> None:
    from datetime import datetime
    import my.core.tests.auto_stats as M

    auto_stats = guess_stats(M.__name__)
    assert auto_stats is not None
    res = auto_stats()

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


def guess_data_providers(module_name: str) -> Dict[str, Callable]:
    module = importlib.import_module(module_name)
    mfunctions = inspect.getmembers(module, inspect.isfunction)
    return {k: v for k, v in mfunctions if is_data_provider(v)}


# todo how to exclude deprecated stuff?
def is_data_provider(fun: Any) -> bool:
    """
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
    if len(list(sig_required_params(sig))) > 0:
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

    return type_is_iterable(return_type)


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

    def has_extra_args(count) -> List[int]:
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


# return any parameters the user is required to provide - those which don't have default values
def sig_required_params(sig: inspect.Signature) -> Iterator[inspect.Parameter]:
    for param in sig.parameters.values():
        if param.default == inspect.Parameter.empty:
            yield param


def test_sig_required_params() -> None:

    def x() -> int:
        return 5
    assert len(list(sig_required_params(inspect.signature(x)))) == 0

    def y(arg: int) -> int:
        return arg
    assert len(list(sig_required_params(inspect.signature(y)))) == 1

    # from stats perspective, this should be treated as a data provider as well
    # could be that the default value to the data provider is the 'default'
    # path to use for inputs/a function to provide input data
    def z(arg: int = 5) -> int:
        return arg
    assert len(list(sig_required_params(inspect.signature(z)))) == 0


def type_is_iterable(type_spec) -> bool:
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
    from typing import List, Sequence, Iterable, Dict, Any

    fun = type_is_iterable
    assert not fun(None)
    assert not fun(int)
    assert not fun(Any)
    assert not fun(Dict[int, int])

    assert fun(List[int])
    assert fun(Sequence[Dict[str, str]])
    assert fun(Iterable[Any])
