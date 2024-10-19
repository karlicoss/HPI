from __future__ import annotations

import datetime
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any, Callable, NamedTuple

from .error import error_to_json
from .pytest import parametrize
from .types import is_namedtuple

# note: it would be nice to combine the 'asdict' and _default_encode to some function
# that takes a complex python object and returns JSON-compatible fields, while still
# being a dictionary.
# a workaround is to encode with dumps below and then json.loads it immediately


DefaultEncoder = Callable[[Any], Any]

Dumps = Callable[[Any], str]


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
    if is_dataclass(obj):
        assert not isinstance(obj, type)  # to help mypy
        return asdict(obj)
    if isinstance(obj, Exception):
        return error_to_json(obj)
    # if something was stored as 'decimal', you likely
    # don't want to convert it to float since you're
    # storing as decimal to not lose the precision
    if isinstance(obj, Decimal):
        return str(obj)
    # note: _serialize would only be called for items which aren't already
    # serialized as a dataclass or namedtuple
    # discussion: https://github.com/karlicoss/HPI/issues/138#issuecomment-801704929
    if hasattr(obj, '_serialize') and callable(obj._serialize):
        return obj._serialize()
    raise TypeError(f"Could not serialize object of type {type(obj).__name__}")


# could possibly run multiple times/raise warning if you provide different 'default'
# functions or change the kwargs? The alternative is to maintain all of this at the module
# level, which is just as annoying
@cache
def _dumps_factory(**kwargs) -> Callable[[Any], str]:
    use_default: DefaultEncoder = _default_encode
    # if the user passed an additional 'default' parameter,
    # try using that to serialize before before _default_encode
    _additional_default: DefaultEncoder | None = kwargs.get("default")
    if _additional_default is not None and callable(_additional_default):

        def wrapped_default(obj: Any) -> Any:
            assert _additional_default is not None
            try:
                return _additional_default(obj)
            except TypeError:
                # expected TypeError, signifies couldn't be encoded by custom
                # serializer function. Try _default_encode from here
                return _default_encode(obj)

        use_default = wrapped_default

    kwargs["default"] = use_default

    prefer_factory: str | None = kwargs.pop('_prefer_factory', None)

    def orjson_factory() -> Dumps | None:
        try:
            import orjson
        except ModuleNotFoundError:
            return None

        # todo: add orjson.OPT_NON_STR_KEYS? would require some bitwise ops
        # most keys are typically attributes from a NT/Dataclass,
        # so most seem to work: https://github.com/ijl/orjson#opt_non_str_keys
        def _orjson_dumps(obj: Any) -> str:  # TODO rename?
            # orjson returns json as bytes, encode to string
            return orjson.dumps(obj, **kwargs).decode('utf-8')

        return _orjson_dumps

    def simplejson_factory() -> Dumps | None:
        try:
            from simplejson import dumps as simplejson_dumps
        except ModuleNotFoundError:
            return None

        # if orjson couldn't be imported, try simplejson
        # This is included for compatibility reasons because orjson
        # is rust-based and compiling on rarer architectures may not work
        # out of the box
        #
        # unlike the builtin JSON module which serializes NamedTuples as lists
        # (even if you provide a default function), simplejson correctly
        # serializes namedtuples to dictionaries

        def _simplejson_dumps(obj: Any) -> str:
            return simplejson_dumps(obj, namedtuple_as_object=True, **kwargs)

        return _simplejson_dumps

    def stdlib_factory() -> Dumps | None:
        import json

        from .warnings import high

        high(
            "You might want to install 'orjson' to support serialization for lots more types! If that does not work for you, you can install 'simplejson' instead"
        )

        def _stdlib_dumps(obj: Any) -> str:
            return json.dumps(obj, **kwargs)

        return _stdlib_dumps

    factories = {
        'orjson': orjson_factory,
        'simplejson': simplejson_factory,
        'stdlib': stdlib_factory,
    }

    if prefer_factory is not None:
        factory = factories[prefer_factory]
        res = factory()
        assert res is not None, prefer_factory
        return res

    for factory in factories.values():
        res = factory()
        if res is not None:
            return res
    raise RuntimeError("Should not happen!")


def dumps(
    obj: Any,
    default: DefaultEncoder | None = None,
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


@parametrize('factory', ['orjson', 'simplejson', 'stdlib'])
def test_dumps(factory: str) -> None:
    import pytest

    orig_dumps = globals()['dumps']  # hack to prevent error from using local variable before declaring

    def dumps(*args, **kwargs) -> str:
        kwargs['_prefer_factory'] = factory
        return orig_dumps(*args, **kwargs)

    import json as json_builtin  # dont cause possible conflicts with module code

    # can't use a namedtuple here, since the default json.dump serializer
    # serializes namedtuples as tuples, which become arrays
    # just test with an array of mixed objects
    X = [5, datetime.timedelta(seconds=5.0)]

    # ignore warnings. depending on test order,
    # the lru_cache'd warning may have already been sent,
    # so checking may be nondeterministic?
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = json_builtin.loads(dumps(X))
        assert res == [5, 5.0]

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

    res = json_builtin.loads(dumps(WithUnderscoreSerialize(6)))
    assert res == {"x": 6, "y": 6.0}

    # test passing additional 'default' func
    def _serialize_with_default(o: Any) -> Any:
        if isinstance(o, Unserializable):
            return {"x": o.x, "y": o.y}
        raise TypeError("Couldn't serialize")

    # this serializes both Unserializable, which is a custom type otherwise
    # not handled, and timedelta, which is handled by the '_default_encode'
    # in the 'wrapped_default' function
    res2 = json_builtin.loads(dumps(Unserializable(10), default=_serialize_with_default))
    assert res2 == {"x": 10, "y": 10.0}

    if factory == 'orjson':
        import orjson

        # test orjson option kwarg
        data = {datetime.date(year=1970, month=1, day=1): 5}
        res2 = json_builtin.loads(dumps(data, option=orjson.OPT_NON_STR_KEYS))
        assert res2 == {'1970-01-01': 5}


@parametrize('factory', ['orjson', 'simplejson'])
def test_dumps_namedtuple(factory: str) -> None:
    import json as json_builtin  # dont cause possible conflicts with module code

    class _A(NamedTuple):
        x: int
        y: float

    res: str = dumps(_A(x=1, y=2.0), _prefer_factory=factory)
    assert json_builtin.loads(res) == {'x': 1, 'y': 2.0}
