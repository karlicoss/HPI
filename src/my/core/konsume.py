'''
Some experimental JSON parsing, basically to ensure that all data is consumed.
This can potentially allow both for safer defensive parsing, and let you know if the data started returning more data

TODO perhaps need to get some inspiration from linear logic to decide on a nice API...
'''

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast


def ignore(w, *keys):
    for k in keys:
        w[k].ignore()


def zoom(w, *keys):
    return [w[k].zoom() for k in keys]


# TODO need to support lists
class Zoomable:
    def __init__(self, parent, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.parent = parent

    # TODO not sure, maybe do it via del??
    # TODO need to make sure they are in proper order? object should be last..
    @property
    def dependants(self):
        raise NotImplementedError

    def ignore(self) -> None:
        self.consume_all()

    def consume_all(self) -> None:
        for d in self.dependants:
            d.consume_all()
        self.consume()

    def consume(self) -> None:
        assert self.parent is not None
        self.parent._remove(self)

    def zoom(self) -> Zoomable:
        self.consume()
        return self

    def _remove(self, xx):
        raise NotImplementedError

    def this_consumed(self):
        raise NotImplementedError


class Wdict(Zoomable, OrderedDict):
    def _remove(self, xx):
        keys = [k for k, v in self.items() if v is xx]
        assert len(keys) == 1
        del self[keys[0]]

    @property
    def dependants(self):
        return list(self.values())

    def this_consumed(self):
        return len(self) == 0

    # TODO specify mypy type for the index special method?


class Wlist(Zoomable, list):
    def _remove(self, xx):
        self.remove(xx)

    @property
    def dependants(self):
        return list(self)

    def this_consumed(self):
        return len(self) == 0


class Wvalue(Zoomable):
    def __init__(self, parent, value: Any) -> None:
        super().__init__(parent)
        self.value = value

    @property
    def dependants(self):
        return []

    def this_consumed(self):
        return True  # TODO not sure..

    def __repr__(self):
        return 'WValue{' + repr(self.value) + '}'


def _wrap(j, parent=None) -> tuple[Zoomable, list[Zoomable]]:
    res: Zoomable
    cc: list[Zoomable]
    if isinstance(j, dict):
        res = Wdict(parent)
        cc = [res]
        for k, v in j.items():
            vv, c = _wrap(v, parent=res)
            res[k] = vv
            cc.extend(c)
        return res, cc
    elif isinstance(j, list):
        res = Wlist(parent)
        cc = [res]
        for i in j:
            ii, c = _wrap(i, parent=res)
            res.append(ii)
            cc.extend(c)
        return res, cc
    elif isinstance(j, (int, float, str, type(None))):
        res = Wvalue(parent, j)
        return res, [res]
    else:
        raise RuntimeError(f'Unexpected type: {type(j)} {j}')


class UnconsumedError(Exception):
    pass


# TODO think about error policy later...
@contextmanager
def wrap(j, *, throw=True) -> Iterator[Zoomable]:
    w, children = _wrap(j)

    yield w

    for c in children:
        if not c.this_consumed():  # TODO hmm. how does it figure out if it's consumed???
            if throw:
                # TODO need to keep a full path or something...
                raise UnconsumedError(f'''
Expected {c} to be fully consumed by the parser.
'''.lstrip())
            else:
                # TODO log?
                pass


def test_unconsumed() -> None:
    import pytest

    with pytest.raises(UnconsumedError):
        with wrap({'a': 1234}) as w:
            w = cast(Wdict, w)

    with pytest.raises(UnconsumedError):
        with wrap({'c': {'d': 2222}}) as w:
            w = cast(Wdict, w)
            _d = w['c']['d'].zoom()


def test_consumed() -> None:
    with wrap({'a': 1234}) as w:
        w = cast(Wdict, w)
        _a = w['a'].zoom()

    with wrap({'c': {'d': 2222}}) as w:
        w = cast(Wdict, w)
        c = w['c'].zoom()
        _d = c['d'].zoom()


def test_types() -> None:
    # (string, number, object, array, boolean or nul
    with wrap({'string': 'string', 'number': 3.14, 'boolean': True, 'null': None, 'list': [1, 2, 3]}) as w:
        w = cast(Wdict, w)
        w['string'].zoom()
        w['number'].consume()
        w['boolean'].zoom()
        w['null'].zoom()
        for x in list(w['list'].zoom()):  # TODO eh. how to avoid the extra list thing?
            x.consume()


def test_consume_all() -> None:
    with wrap({'aaa': {'bbb': {'hi': 123}}}) as w:
        w = cast(Wdict, w)
        aaa = w['aaa'].zoom()
        aaa['bbb'].consume_all()


def test_consume_few() -> None:
    import pytest

    pytest.skip('Will think about it later..')
    with wrap({'important': 123, 'unimportant': 'whatever'}) as w:
        w = cast(Wdict, w)
        w['important'].zoom()
        w.consume_all()
        # TODO hmm, we want smth like this to work..


def test_zoom() -> None:
    import pytest

    with wrap({'aaa': 'whatever'}) as w:
        w = cast(Wdict, w)
        with pytest.raises(KeyError):
            w['nosuchkey'].zoom()
        w['aaa'].zoom()


# TODO type check this...

# TODO feels like the whole thing kind of unnecessarily complex
# - cons:
#     - in most cases this is not even needed? who cares if we miss a few attributes?
# - pro: on the other hand it could be interesting to know about new attributes in data,
#        and without this kind of processing we wouldn't even know
# alternatives
# - manually process data
#   e.g. use asserts, dict.pop and dict.values() methods to unpack things
#   - pros:
#     - very simple, since uses built in syntax
#     - very performant, as fast as it gets
#     - very flexible, easy to adjust behaviour
#   - cons:
#     - can forget to assert about extra entities etc, so error prone
#     - if we do something like =assert j.pop('status') == 200, j=, by the time assert happens we already popped item -- makes error handling harder
#     - a bit verbose.. so probably requires some helper functions though (could be much leaner than current konsume though)
#     - if we assert, then terminates parsing too early, if we're defensive then inflates the code a lot with if statements
#       - TODO perhaps combine warnings somehow or at least only emit once per module?
#       - hmm actually tbh if we carefully go through everything and don't make copies, then only requires one assert at the very end?
#   - TODO this is kinda useful? https://discuss.python.org/t/syntax-for-dictionnary-unpacking-to-variables/18718
#     operator.itemgetter?
#   - TODO can use match operator in python for this? quite nice actually! and allows for dynamic behaviour
#     only from 3.10 tho, and gonna be tricky to do dynamic defensive behaviour with this
#   - TODO in a sense, blenser already would hint if some meaningful fields aren't being processed? only if they are changing though
# - define a "schema" for data, then just recursively match data against the schema?
#   possibly pydantic already does something like that? not sure about performance though
#   pros:
#     - much simpler to extend and understand what's going on
#   cons:
#     - more rigid, so it becomes tricky to do dynamic stuff (e.g. if schema actually changes)
