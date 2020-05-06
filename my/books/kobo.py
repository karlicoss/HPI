"""
[[https://uk.kobobooks.com/products/kobo-aura-one][Kobo]] e-ink reader: annotations and reading stats
"""
from typing import Callable, Union, List

from my.config import kobo as config
from my.config.repos.kobuddy.src.kobuddy import *
# hmm, explicit imports make pylint a bit happier..
from my.config.repos.kobuddy.src.kobuddy import Highlight, set_databases, get_highlights

set_databases(config.export_dir)

# TODO maybe type over T?
_Predicate = Callable[[str], bool]
Predicatish = Union[str, _Predicate]
def from_predicatish(p: Predicatish) -> _Predicate:
    if isinstance(p, str):
        def ff(s):
            return s == p
        return ff
    else:
        return p


def by_annotation(predicatish: Predicatish, **kwargs) -> List[Highlight]:
    pred = from_predicatish(predicatish)

    res: List[Highlight] = []
    for h in get_highlights(**kwargs):
        if pred(h.annotation):
            res.append(h)
    return res


def get_todos():
    def with_todo(ann):
        if ann is None:
            ann = ''
        return 'todo' in ann.lower().split()
    return by_annotation(with_todo)


def test_todos():
    todos = get_todos()
    assert len(todos) > 3
