from typing import Any

from .common import is_namedtuple
from .error import error_to_json

# note: it would be nice to combine the 'asdict' and _orjson_default to some function
# that takes a complex python object and returns JSON-compatible fields, while still
# being a dictionary.
# a workaround is to encode with dumps below and then json.loads it immediately


def _orjson_default(obj: Any) -> Any:
    """
    Encodes complex python datatypes to simpler representations,
    before they're serialized to JSON string
    """
    # orjson doesn't serialize namedtuples to avoid serializing
    # them as tuples (arrays), since they're technically a subclass
    if is_namedtuple(obj):
        return obj._asdict()
    if isinstance(obj, Exception):
        err = error_to_json(obj)
        # remove unrelated dt key? maybe error_to_json should be refactored?
        err.pop('dt', None)
        return err
    raise TypeError(f"Could not serialize object of type {obj.__type__.__name__}")


def dumps(obj: Any) -> str:
    try:
        import orjson
        # serialize 'b'"1970-01-01T00:00:00"' instead of b'"1970-01-01T00:00:00.000000"
        opts = orjson.OPT_OMIT_MICROSECONDS
        json_bytes = orjson.dumps(obj, default=_orjson_default, option=opts)
        return json_bytes.decode('utf-8')
    except ModuleNotFoundError:
        import warnings
        warnings.warn("You might want to install 'orjson' to support serialization for lots more types!")
        import json
        return json.dumps(obj, default=_orjson_default)
