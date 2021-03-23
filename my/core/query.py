"""
This lets you query, order, sort and filter items from one or more sources

The main entrypoint to this library is the 'select' function below; try:
python3 -c "from my.core.query import select; help(select)"
"""

import re
import dataclasses
import importlib
import inspect
import itertools
from datetime import datetime, date, timedelta
from typing import TypeVar, Tuple, Optional, Union, Callable, Iterable, Iterator, Dict, Any

import more_itertools

from .warnings import low
from .common import is_namedtuple
from .error import Res, unwrap
from .warnings import low


T = TypeVar("T")
ET = Res[T]


# e.g. ("my.reddit", "comments")
Locator = Tuple[str, str]
U = TypeVar("U")
# In a perfect world, the return value from a OrderFunc would just be U,
# not Optional[U]. However, since this has to deal with so many edge
# cases, theres a possibility that the functions generated by
# _generate_order_by_func can't find an attribute
OrderFunc = Callable[[ET], Optional[U]]
Where = Callable[[ET], bool]

DateLike = Union[datetime, date]


class QueryException(KeyError):
    """Used to differentiate query-related errors, so the CLI interface is more expressive"""
    pass


def locate_function(module_name: str, function_name: str) -> Callable[[], Iterable[ET]]:
    """
    Given a module name and a function, returns the corresponding function.
    Since we're in the query module, it is assumed that this returns an
    iterable of objects of some kind, which we want to query over, though
    that isn't required
    """
    try:
        mod = importlib.import_module(module_name)
        for (fname, func) in inspect.getmembers(mod, inspect.isfunction):
            if fname == function_name:
                return func
    except Exception as e:
        raise QueryException(str(e))
    raise QueryException(f"Could not find function {function_name} in {module_name}")


timedelta_regex = re.compile(r"^((?P<days>[\.\d]+?)d)?((?P<hours>[\.\d]+?)h)?((?P<minutes>[\.\d]+?)m)?((?P<seconds>[\.\d]+?)s)?$")


# https://stackoverflow.com/a/51916936
def parse_timedelta_string(timedelta_str: str) -> timedelta:
    """
    This uses a syntax similar to the 'GNU sleep' command
    e.g.: 10d5h10m50s means '10 days, 5 hours, 10 minutes, 50 seconds'
    """
    parts = timedelta_regex.match(timedelta_str)
    if parts is None:
        raise ValueError(f"Could not parse time duration from {timedelta_str}.\nValid examples: '8h', '2d8h5m20s', '2m4s'")
    time_params = {name: float(param) for name, param in parts.groupdict().items() if param}
    return timedelta(**time_params)  # type: ignore[arg-type]



def _generate_order_by_func(
        obj_res: Res[T],
        key: Optional[str] = None,
        where_function: Optional[Where] = None,
        default: Optional[U] = None
) -> Optional[OrderFunc]:
    """
    Accepts an object Res[T] (Instance of some class or Exception)

    If its an error, the generated function returns None

    Most of the time, you'd want to provide at least a 'key', a 'where_function' or a 'default'.
    You can provide both a 'where_function' and a default, or a 'key' and a default,
    incase the 'where_function' doesn't work for a particular type/you hit an error

    If a 'default' is provided, it is used for Exceptions and if an
    OrderFunc function could not be determined for this type

    If a key is given (the user specified which attribute), the function
    returns that key from the object
    tries to find that key on the object

    Attempts to find an attribute which matches the 'where_function' on the object,
    using some getattr/dict checks. Returns a function which when called with
    this object returns the value to order by
    """
    if isinstance(obj_res, Exception):
        if default is not None:
            return lambda _o: default
        else:
            low(f"""While creating order_by function, encountered exception {obj_res}
Value to order_by unknown, provide a 'default', filter exceptons with a 'where' predicate or
pass 'drop_errors' to ignore this""")
            return lambda _o: None

    # shouldn't raise an error, as we return above if its an exception
    obj: T = unwrap(obj_res)

    if key is not None:

        # in these cases, if your key existed on the initial Res[E] (instance that was passed to
        # _generate_order_by_func and generates the OrderFunc)
        # to run, but doesn't on others, it will return None in those cases
        # If the interface to your ADT is not standard or very sparse, its better
        # that you manually write an OrderFunc which
        # handles the edge cases, or provide a default
        # See tests for an example
        # TODO: write test
        if isinstance(obj, dict):
            if key in obj:  # acts as predicate instead of where_function
                return lambda o: o.get(key, default)  # type: ignore[union-attr]
        else:
            if hasattr(obj, key):
                return lambda o: getattr(o, key, default)  # type: ignore[arg-type]

    # Note: if the attribute you're ordering by is an Optional type,
    # and on some objects it'll return None, the getattr(o, field_name, default) won't
    # use the default, since it finds the attribute (it just happens to be set to None)
    # should this do something like: 'lambda o: getattr(o, k, default) or default'
    # that would fix the case, but is additional work. Perhaps the user should instead
    # write a 'where' function, to check for that 'isinstance' on an Optional field,
    # and not include those objects in the src iterable

    # user must provide either a key or a where predicate
    if where_function is not None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if where_function(v):
                    return lambda o: o.get(k, default)  # type: ignore[union-attr]
        elif dataclasses.is_dataclass(obj):
            for (field_name, _annotation) in obj.__annotations__.items():
                if where_function(getattr(obj, field_name)):
                    return lambda o: getattr(o, field_name, default)
        elif is_namedtuple(obj):
            assert hasattr(obj, '_fields'), "Could not find '_fields' on attribute which is assumed to be a NamedTuple"
            for field_name in getattr(obj, '_fields'):
                if where_function(getattr(obj, field_name)):
                    return lambda o: getattr(o, field_name, default)
        # try using inpsect.getmembers (like 'dir()') even if the dataclass/NT checks failed,
        # since the attribute one is searching for might be a @property
        for k, v in inspect.getmembers(obj):
            if where_function(v):
                return lambda o: getattr(o, k, default)

    if default is not None:
        # warn here? it seems like you typically wouldn't want to just set the order by to
        # the same value everywhere, but maybe you did this on purpose?
        return lambda _o: default

    return None  # couldn't compute a OrderFunc for this class/instance


def _drop_errors(itr: Iterator[ET]) -> Iterator[T]:
    """Return non-errors from the iterable"""
    for o in itr:
        if isinstance(o, Exception):
            continue
        yield o

def _raise_errors(itr: Iterable[ET]) -> Iterator[T]:
    """Raise errors from the iterable, stops the select function"""
    for o in itr:
        if isinstance(o, Exception):
            raise o
        yield o


# currently using the 'key set' as a proxy for 'this is the same type of thing'
def _determine_order_by_value_key(obj_res: ET) -> Any:
    """
    Returns either the class, or the a tuple of the dictionary keys
    """
    key = obj_res.__class__
    if key == dict:
        # assuming same keys signify same way to determine ordering
        return tuple(obj_res.keys())  # type: ignore[union-attr]
    return key


def select(
    src: Union[Locator, Iterable[ET], Callable[[], Iterable[ET]]],
    *,
    where: Optional[Where] = None,
    order_by: Optional[OrderFunc] = None,
    order_key: Optional[str] = None,
    order_value: Optional[Where] = None,
    default: Optional[U] = None,
    reverse: bool = False,
    limit: Optional[int] = None,
    drop_errors: bool = False,
    raise_errors: bool = False,
) -> Iterator[ET]:
    """
    A function to query, order, sort and filter items from one or more sources
    This supports iterables and lists of mixed types (including handling errors),
    by allowing you to provide custom predicates (functions) which can sort
    by a function, an attribute, dict key, or by the attributes values.

    Since this supports mixed types, theres always a possibility
    of KeyErrors or AttributeErrors while trying to find some value to order by,
    so this provides multiple mechanisms to deal with that

    'where' lets you filter items before ordering, to remove possible errors
    or filter the iterator by some condition

    There are multiple ways to instruct select on how to order items. The most
    flexible is to provide an 'order_by' function, which takes an item in the
    iterator, does any custom checks you may want and then returns the value to sort by

    'order_key' is best used on items which have a similar structure, or have
    the same attribute name for every item in the iterator. If you have a
    iterator of objects whose datetime is accessed by the 'timestamp' attribute,
    supplying order_key='timestamp' would sort by that (dictionary or attribute) key

    'order_value' is the most confusing, but often the most useful. Instead of
    testing against the keys of an item, this allows you to write a predicate
    (function) to test against its values (dictionary, NamedTuple, dataclass, object).
    If you had an iterator of mixed types and wanted to sort by the datetime,
    but the attribute to access the datetime is different on each type, you can
    provide `order_value=lambda v: isinstance(v, datetime)`, and this will
    try to find that value for each type in the iterator, to sort it by
    the value which is recieved when the predicate is true

    'order_value' is often used in the 'hpi query' interface, because of its brevity.
    Just given the input function, this can typically sort it by timestamp with
    no human intervention. It can sort of be thought as an educated guess,
    but it can always be improved by providing a more complete guess function

    Note that 'order_value' is also the most computationally expensive, as it has
    to copy the iterator in memory (using itertools.tee) to determine how to order it
    in memory

    The 'drop_errors' and 'raise_errors' let you ignore or raise when the src contain errors

    src:            a locator to import a function from, an iterable of mixed types,
                    or a function to be called, as the input to this function

    where:          a predicate which filters the results before sorting

    order_by:       a function which when given an item in the src,
                    returns the value to sort by. Similar to the 'key' value
                    tpically passed directly to 'sorted'

    order_key:      a string which represents a dict key or attribute name
                    to use as they key to sort by

    order_value:    predicate which determines which attribute on an ADT-like item to sort by,
                    when given its value. lambda o: isinstance(o, datetime) is commonly passed to sort
                    by datetime, without knowing the attributes or interface for the items in the src

    default:        while ordering, if the order for an object cannot be determined,
                    use this as the default value

    reverse:        reverse the order of the resulting iterable

    limit:          limit the results to this many items

    drop_errors:    ignore any errors from the src

    raise_errors:   raise errors when recieved from the input src
    """

    it: Iterable[ET] = []  # default
    # check if this is a locator
    if type(src) == tuple and len(src) == 2:  # type: ignore[arg-type]
        it = locate_function(src[0], src[1])()  # type: ignore[index]
    elif callable(src):
        # hopefully this returns an iterable and not something that causes a bunch of lag when its called?
        # should typically not be the common case, but giving the option to
        # provide a function as input anyways
        it = src()
    else:
        # assume it is already an iterable
        if not isinstance(src, Iterable):
            low(f"""Input was neither a locator for a function, or a function itself.
Expected 'src' to be an Iterable, but found {type(src).__name__}...
Will attempt to call iter() on the value""")
        it = src

    # try/catch an explicit iter() call to making this an Iterator,
    # to validate the input as something other helpers here can work with,
    # else raise a QueryException
    try:
        itr: Iterator[ET] = iter(it)
    except TypeError as t:
        raise QueryException("Could not convert input src to an Iterator: " + str(t))

    # if both drop_errors and raise_errors are provided for some reason,
    # should raise errors before dropping them
    if raise_errors:
        itr = _raise_errors(itr)

    if drop_errors:
        itr = _drop_errors(itr)

    if where is not None:
        itr = filter(where, itr)

    if order_by is not None or order_key is not None or order_value is not None:
        # we have some sort of input that specifies we should reorder the iterator

        order_by_chosen: Optional[OrderFunc] = order_by  # if the user just supplied a function themselves
        if order_by is None:
            # https://more-itertools.readthedocs.io/en/stable/api.html#more_itertools.spy
            [first_item], itrc = more_itertools.spy(itr)
            # replace the 'itr' in the higher scope with itrc -- itr is consumed by more_itertools.spy
            itr = itrc
            # try to use a key, if it was supplied
            # order_key doesn't use local state - it just tries to find the passed
            # attribute, or default to the 'default' value. As mentioned above,
            # best used for items with a similar structure
            if order_key is not None:
                order_by_chosen = _generate_order_by_func(first_item, key=order_key, default=default)
                if order_by_chosen is None:
                    raise QueryException(f"Error while ordering: could not find {order_key} on {first_item}")
            elif order_value is not None:
                itr1, itr2 = itertools.tee(itr, 2)  # expensive!!!
                # TODO: add a kwarg to force lookup for every item? would sort of be like core.common.guess_datetime then
                order_by_lookup: Dict[Any, OrderFunc] = {}

                # need to go through a copy of the whole iterator here to
                # pre-generate functions to support sorting mixed types
                for obj_res in itr1:
                    key: Any = _determine_order_by_value_key(obj_res)
                    if key not in order_by_lookup:
                        keyfunc: Optional[OrderFunc] = _generate_order_by_func(obj_res, where_function=order_value, default=default)
                        if keyfunc is None:
                            raise QueryException(f"Error while ordering: could not determine how to order {obj_res}")
                        order_by_lookup[key] = keyfunc

                # set the 'itr' (iterator in higher scope)
                # to the copy (itertools.tee) of the iterator we haven't used yet
                itr = itr2

                # todo: cache results from above _determine_order_by_value_key call and use here somehow?
                # would require additional state
                # order_by_lookup[_determine_order_by_value_key(o)] returns a function which
                # accepts o, and returns the value which sorted can use to order this by
                order_by_chosen = lambda o: order_by_lookup[_determine_order_by_value_key(o)](o)

        # run the sort, with the computed order by function
        itr = iter(sorted(itr, key=order_by_chosen, reverse=reverse))  # type: ignore[arg-type]
    else:
        # if not already done in the order_by block, reverse if specified
        if reverse:
            itr = more_itertools.always_reversible(itr)

    # apply limit argument
    if limit is not None:
        return itertools.islice(itr, limit)

    return itr



def test_parse_timedelta_string():

    import pytest

    with pytest.raises(ValueError) as v:
        parse_timedelta_string("5xxx")

    assert v is not None
    assert str(v.value).startswith("Could not parse time duration from")

    res = parse_timedelta_string("10d5h10m50s")
    assert res == timedelta(days=10.0, hours=5.0, minutes=10.0, seconds=50.0)
