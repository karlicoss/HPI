'''
Helpers for hpi doctor/stats functionality.
'''
import collections
import importlib
import inspect
import sys
import typing
from typing import Optional, Callable, Any, Iterator, Sequence, Dict

from .common import StatsFun, Stats, stat


# TODO maybe could be enough to annotate OUTPUTS or something like that?
# then stats could just use them as hints?
def guess_stats(module_name: str, quick: bool=False) -> Optional[StatsFun]:
    providers = guess_data_providers(module_name)
    if len(providers) == 0:
        return None
    def auto_stats() -> Stats:
        return {k: stat(v, quick=quick) for k, v in providers.items()}
    return auto_stats


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
    4. functions isnt the 'inputs' function (or ends with '_inputs')
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
        # ignore def inputs; something like comment_inputs or backup_inputs should also be ignored
        if fun.__name__ == 'inputs' or fun.__name__.endswith('_inputs'):
            return False

    return_type = sig.return_annotation
    return type_is_iterable(return_type)


def test_is_data_provider() -> None:
    idp = is_data_provider
    assert not idp(None)
    assert not idp(int)
    assert not idp("x")

    def no_return_type():
        return [1, 2 ,3]
    assert not idp(no_return_type)

    lam = lambda: [1, 2]
    assert not idp(lam)

    def has_extra_args(count) -> typing.List[int]:
        return list(range(count))
    assert not idp(has_extra_args)

    def has_return_type() -> typing.Sequence[str]:
        return ['a', 'b', 'c']
    assert idp(has_return_type)

    def _helper_func() -> Iterator[Any]:
        yield 1
    assert not idp(_helper_func)

    def inputs() -> Iterator[Any]:
        yield 1
    assert not idp(inputs)

    def producer_inputs() -> Iterator[Any]:
        yield 1
    assert not idp(producer_inputs)



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
    if sys.version_info[1] < 8:
        # there is no get_origin before 3.8, and retrofitting gonna be a lot of pain
        return any(x in str(type_spec) for x in ['List', 'Sequence', 'Iterable', 'Iterator'])
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
