import datetime
import dataclasses
from pathlib import Path
from typing import Any, Optional, Callable, NamedTuple
from functools import lru_cache

from .common import is_namedtuple
from .error import error_to_json

# note: it would be nice to combine the 'asdict' and _default_encode to some function
# that takes a complex python object and returns JSON-compatible fields, while still
# being a dictionary.
# a workaround is to encode with dumps below and then json.loads it immediately


DefaultEncoder = Callable[[Any], Any]


def _default_encode(obj: Any) -> Any:
    """
    Encodes complex python datatypes to simpler representations,
    before they're serialized to JSON string
    """
    # orjson doesn't serialize namedtuples to avoid serializing
    # them as tuples (arrays), since they're technically a subclass
    if is_namedtuple(obj):
        return obj._asdict()
    if isinstance(obj, datetime.timedelta):
        return obj.total_seconds()
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        return str(obj)
    # convert paths to their string representation
    if isinstance(obj, Path):
        return str(obj)
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, Exception):
        return error_to_json(obj)
    # note: _serialize would only be called for items which aren't already
    # serialized as a dataclass or namedtuple
    # discussion: https://github.com/karlicoss/HPI/issues/138#issuecomment-801704929
    if hasattr(obj, '_serialize') and callable(obj._serialize):
        return obj._serialize()
    raise TypeError(f"Could not serialize object of type {type(obj).__name__}")


# could possibly run multiple times/raise warning if you provide different 'default'
# functions or change the kwargs? The alternative is to maintain all of this at the module
# level, which is just as annoying
@lru_cache(maxsize=None)
def _dumps_factory(**kwargs) -> Callable[[Any], str]:
    use_default: DefaultEncoder = _default_encode
    # if the user passed an additional 'default' parameter,
    # try using that to serialize before before _default_encode
    _additional_default: Optional[DefaultEncoder] = kwargs.get("default")
    if _additional_default is not None and callable(_additional_default):

        def wrapped_default(obj: Any) -> Any:
            try:
                # hmm... shouldn't mypy know that _additional_default is not None here?
                # assert _additional_default is not None
                return _additional_default(obj)  # type: ignore[misc]
            except TypeError:
                # expected TypeError, signifies couldn't be encoded by custom
                # serializer function. Try _default_encode from here
                return _default_encode(obj)

        use_default = wrapped_default

    kwargs["default"] = use_default

    try:
        import orjson

        # todo: add orjson.OPT_NON_STR_KEYS? would require some bitwise ops
        # most keys are typically attributes from a NT/Dataclass,
        # so most seem to work: https://github.com/ijl/orjson#opt_non_str_keys
        def _orjson_dumps(obj: Any) -> str:
            # orjson returns json as bytes, encode to string
            return orjson.dumps(obj, **kwargs).decode('utf-8')

        return _orjson_dumps
    except ModuleNotFoundError:
        pass

    try:
        from simplejson import dumps as simplejson_dumps
        # if orjson couldn't be imported, try simplejson
        # This is included for compatibility reasons because orjson
        # is rust-based and compiling on rarer architectures may not work
        # out of the box
        #
        # unlike the builtin JSON modue which serializes NamedTuples as lists
        # (even if you provide a default function), simplejson correctly
        # serializes namedtuples to dictionaries

        def _simplejson_dumps(obj: Any) -> str:
            return simplejson_dumps(obj, namedtuple_as_object=True, **kwargs)

        return _simplejson_dumps

    except ModuleNotFoundError:
        pass

    import json
    from .warnings import high

    high("You might want to install 'orjson' to support serialization for lots more types! If that does not work for you, you can install 'simplejson' instead")

    def _stdlib_dumps(obj: Any) -> str:
        return json.dumps(obj, **kwargs)

    return _stdlib_dumps


def dumps(
    obj: Any,
    default: Optional[DefaultEncoder] = None,
    **kwargs,
) -> str:
    """
    Any additional arguments are forwarded -- either to orjson.dumps,
    simplejson.dumps or json.dumps if orjson is not installed

    You can pass the 'option' kwarg to orjson, see here for possible options:
    https://github.com/ijl/orjson#option

    Any class/instance can implement a `_serialize` function, which is used
    to convert it to a JSON-compatible representation.
    If present, it is called during _default_encode

    'default' is called before _default_encode, and should raise a TypeError if
    its not able to serialize the type. As an example:

    from my.core.serialize import dumps

    class MyClass:
        def __init__(self, x):
            self.x = x

    def serialize_default(o: Any) -> Any:
        if isinstance(o, MyClass):
            return {"x": o.x}
        raise TypeError("Could not serialize...")

    dumps({"info": MyClass(5)}, default=serialize_default)
    """
    return _dumps_factory(default=default, **kwargs)(obj)


def test_serialize_fallback() -> None:
    import json as jsn  # dont cause possible conflicts with module code

    import pytest

    # cant use a namedtuple here, since the default json.dump serializer
    # serializes namedtuples as tuples, which become arrays
    # just test with an array of mixed objects
    X = [5, datetime.timedelta(seconds=5.0)]

    # ignore warnings. depending on test order,
    # the lru_cache'd warning may have already been sent,
    # so checking may be nondeterministic?
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = jsn.loads(dumps(X))
        assert res == [5, 5.0]



# this needs to be defined here to prevent a mypy bug
# see https://github.com/python/mypy/issues/7281
class _A(NamedTuple):
    x: int
    y: float


def test_nt_serialize() -> None:
    import json as jsn  # dont cause possible conflicts with module code
    import orjson  # import to make sure this is installed

    res: str = dumps(_A(x=1, y=2.0))
    assert res == '{"x":1,"y":2.0}'

    # test orjson option kwarg
    data = {datetime.date(year=1970, month=1, day=1): 5}
    res = jsn.loads(dumps(data, option=orjson.OPT_NON_STR_KEYS))
    assert res == {'1970-01-01': 5}


def test_default_serializer() -> None:
    import pytest
    import json as jsn  # dont cause possible conflicts with module code

    class Unserializable:
        def __init__(self, x: int):
            self.x = x
            # add something handled by the _default_encode function
            self.y = datetime.timedelta(seconds=float(x))

    with pytest.raises(TypeError):
        dumps(Unserializable(5))

    class WithUnderscoreSerialize(Unserializable):
        def _serialize(self) -> Any:
            return {"x": self.x, "y": self.y}

    res = jsn.loads(dumps(WithUnderscoreSerialize(6)))
    assert res == {"x": 6, "y": 6.0}

    # test passing additional 'default' func
    def _serialize_with_default(o: Any) -> Any:
        if isinstance(o, Unserializable):
            return {"x": o.x, "y": o.y}
        raise TypeError("Couldnt serialize")

    # this serializes both Unserializable, which is a custom type otherwise
    # not handled, and timedelta, which is handled by the '_default_encode'
    # in the 'wrapped_default' function
    res2 = jsn.loads(dumps(Unserializable(10), default=_serialize_with_default))
    assert res2 == {"x": 10, "y": 10.0}
