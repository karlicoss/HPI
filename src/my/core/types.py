from __future__ import annotations

from dataclasses import asdict as dataclasses_asdict
from dataclasses import is_dataclass
from datetime import datetime
from typing import Any

Json = dict[str, Any]


# for now just serves documentation purposes... but one day might make it statically verifiable where possible?
# TODO e.g. maybe use opaque mypy alias?
datetime_naive = datetime
datetime_aware = datetime


def is_namedtuple(thing: Any) -> bool:
    # basic check to see if this is namedtuple-like
    _asdict = getattr(thing, '_asdict', None)
    return (_asdict is not None) and callable(_asdict)


def asdict(thing: Any) -> Json:
    # todo primitive?
    # todo exception?
    if isinstance(thing, dict):
        return thing
    if is_dataclass(thing):
        assert not isinstance(thing, type)  # to help mypy
        return dataclasses_asdict(thing)
    if is_namedtuple(thing):
        return thing._asdict()
    raise TypeError(f'Could not convert object {thing} to dict')
