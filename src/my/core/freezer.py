from __future__ import annotations

import dataclasses
import inspect
from typing import Any, Generic, TypeVar

D = TypeVar('D')


def _freeze_dataclass(Orig: type[D]):
    ofields = [(f.name, f.type, f) for f in dataclasses.fields(Orig)]  # type: ignore[arg-type]  # see https://github.com/python/typing_extensions/issues/115

    # extract properties along with their types
    props = list(inspect.getmembers(Orig, lambda o: isinstance(o, property)))
    pfields = [(name, inspect.signature(getattr(prop, 'fget')).return_annotation) for name, prop in props]
    # FIXME not sure about name?
    # NOTE: sadly passing bases=[Orig] won't work, python won't let us override properties with fields
    RRR = dataclasses.make_dataclass('RRR', fields=[*ofields, *pfields])
    # todo maybe even declare as slots?
    return props, RRR


class Freezer(Generic[D]):
    '''
    Some magic which converts dataclass properties into fields.
    It could be useful for better serialization, for performance, for using type as a schema.
    For now only supports dataclasses.
    '''

    def __init__(self, Orig: type[D]) -> None:
        self.Orig = Orig
        self.props, self.Frozen = _freeze_dataclass(Orig)

    def freeze(self, value: D) -> D:
        pvalues = {name: getattr(value, name) for name, _ in self.props}
        return self.Frozen(**dataclasses.asdict(value), **pvalues)  # type: ignore[call-overload]  # see https://github.com/python/typing_extensions/issues/115


### tests


# this needs to be defined here to prevent a mypy bug
# see https://github.com/python/mypy/issues/7281
@dataclasses.dataclass
class _A:
    x: Any

    # TODO what about error handling?
    @property
    def typed(self) -> int:
        return self.x['an_int']

    @property
    def untyped(self):
        return self.x['an_any']


def test_freezer() -> None:
    val = _A(x={
        'an_int': 123,
        'an_any': [1, 2, 3],
    })
    af = Freezer(_A)
    fval = af.freeze(val)

    fd = vars(fval)
    assert fd['typed']   == 123
    assert fd['untyped'] == [1, 2, 3]


###

# TODO shit. what to do with exceptions?
# e.g. good testcase is date parsing issue. should def yield Exception in this case
# fundamentally it should just be Exception aware, dunno
#
# TODO not entirely sure if best to use Frozen as the schema, or actually convert objects..
# guess need to experiment and see
