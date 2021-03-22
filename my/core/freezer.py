from .common import assert_subpackage; assert_subpackage(__name__)

import dataclasses as dcl
import inspect
from typing import TypeVar, Type, Any

D = TypeVar('D')


def _freeze_dataclass(Orig: Type[D]):
    ofields = [(f.name, f.type, f) for f in dcl.fields(Orig)]

    # extract properties along with their types
    props   = list(inspect.getmembers(Orig, lambda o: isinstance(o, property)))
    pfields = [(name, inspect.signature(getattr(prop, 'fget')).return_annotation) for name, prop in props]
    # FIXME not sure about name?
    # NOTE: sadly passing bases=[Orig] won't work, python won't let us override properties with fields
    RRR = dcl.make_dataclass('RRR', fields=[*ofields, *pfields])
    # todo maybe even declare as slots?
    return props, RRR


# todo need some decorator thingie?
from typing import Generic
class Freezer(Generic[D]):
    '''
    Some magic which converts dataclass properties into fields.
    It could be useful for better serialization, for performance, for using type as a schema.
    For now only supports dataclasses.
    '''

    def __init__(self, Orig: Type[D]) -> None:
        self.Orig = Orig
        self.props, self.Frozen = _freeze_dataclass(Orig)

    def freeze(self, value: D) -> D:
        pvalues = {name: getattr(value, name) for name, _ in self.props}
        return self.Frozen(**dcl.asdict(value), **pvalues)


### tests


# this needs to be defined here to prevent a mypy bug
# see https://github.com/python/mypy/issues/7281
@dcl.dataclass
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

    val = _A(x=dict(an_int=123, an_any=[1, 2, 3]))
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
