'''
Some experimental JSON parsing, basically to ensure that all data is consumed.
This can potentially allow both for safer defensive parsing, and let you know if the data started returning more data

TODO perhaps need to get some inspiration from linear logic to decide on a nice API...
'''

from collections import OrderedDict
from typing import Any, List


def ignore(w, *keys):
    for k in keys:
        w[k].ignore()

def zoom(w, *keys):
    return [w[k].zoom() for k in keys]

# TODO need to support lists
class Zoomable:
    def __init__(self, parent, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs) # type: ignore
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

    def zoom(self) -> 'Zoomable':
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
        return True # TODO not sure..

    def __repr__(self):
        return 'WValue{' + repr(self.value) + '}'

from typing import Tuple
def _wrap(j, parent=None) -> Tuple[Zoomable, List[Zoomable]]:
    res: Zoomable
    cc: List[Zoomable]
    if isinstance(j, dict):
        res = Wdict(parent)
        cc = [res]
        for k, v in j.items():
            vv, c  = _wrap(v, parent=res)
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

from contextlib import contextmanager
from typing import Iterator

class UnconsumedError(Exception):
    pass

# TODO think about error policy later...
@contextmanager
def wrap(j, throw=True) -> Iterator[Zoomable]:
    w, children = _wrap(j)

    yield w

    for c in children:
        if not c.this_consumed(): # TODO hmm. how does it figure out if it's consumed???
            if throw:
                # TODO need to keep a full path or something...
                raise UnconsumedError(f'''
Expected {c} to be fully consumed by the parser.
'''.lstrip())
            else:
                # TODO log?
                pass

from typing import cast
def test_unconsumed():
    import pytest # type: ignore
    with pytest.raises(UnconsumedError):
        with wrap({'a': 1234}) as w:
            w = cast(Wdict, w)
            pass

    with pytest.raises(UnconsumedError):
        with wrap({'c': {'d': 2222}}) as w:
            w = cast(Wdict, w)
            d = w['c']['d'].zoom()

def test_consumed():
    with wrap({'a': 1234}) as w:
        w = cast(Wdict, w)
        a = w['a'].zoom()

    with wrap({'c': {'d': 2222}}) as w:
        w = cast(Wdict, w)
        c = w['c'].zoom()
        d = c['d'].zoom()

def test_types():
    # (string, number, object, array, boolean or nul
    with wrap({'string': 'string', 'number': 3.14, 'boolean': True, 'null': None, 'list': [1, 2, 3]}) as w:
        w = cast(Wdict, w)
        w['string'].zoom()
        w['number'].consume()
        w['boolean'].zoom()
        w['null'].zoom()
        for x in list(w['list'].zoom()): # TODO eh. how to avoid the extra list thing?
            x.consume()

def test_consume_all():
    with wrap({'aaa': {'bbb': {'hi': 123}}}) as w:
        w = cast(Wdict, w)
        aaa = w['aaa'].zoom()
        aaa['bbb'].consume_all()


def test_consume_few():
    import pytest
    pytest.skip('Will think about it later..')
    with wrap({
            'important': 123,
            'unimportant': 'whatever'
    }) as w:
        w = cast(Wdict, w)
        w['important'].zoom()
        w.consume_all()
        # TODO hmm, we want smth like this to work..


def test_zoom() -> None:
    import pytest # type: ignore
    with wrap({'aaa': 'whatever'}) as w:
        w = cast(Wdict, w)
        with pytest.raises(KeyError):
            w['nosuchkey'].zoom()
        w['aaa'].zoom()


# TODO type check this...
