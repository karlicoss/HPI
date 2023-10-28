"""
[[https://uk.kobobooks.com/products/kobo-aura-one][Kobo]] e-ink reader: annotations and reading stats
"""
from __future__ import annotations

REQUIRES = [
    'kobuddy',
]

from dataclasses import dataclass
from typing import Iterator

from my.core import (
    get_files,
    stat,
    Paths,
    Stats,
)
from my.core.cfg import make_config
import my.config

import kobuddy
from kobuddy import Highlight, get_highlights
from kobuddy import *


@dataclass
class kobo(my.config.kobo):
    '''
    Uses [[https://github.com/karlicoss/kobuddy#as-a-backup-tool][kobuddy]] outputs.
    '''

    # path[s]/glob to the exported databases
    export_path: Paths


config = make_config(kobo)

# TODO not ideal to set it here.. should switch kobuddy to use a proper DAL
kobuddy.DATABASES = list(get_files(config.export_path))


def highlights() -> Iterator[Highlight]:
    return kobuddy._iter_highlights()


def stats() -> Stats:
    return stat(highlights)


## TODO hmm. not sure if all this really belongs here?... perhaps orger?


from typing import Callable, Union, List

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


def get_todos() -> List[Highlight]:
    def with_todo(ann):
        if ann is None:
            ann = ''
        return 'todo' in ann.lower().split()

    return by_annotation(with_todo)


def test_todos() -> None:
    todos = get_todos()
    assert len(todos) > 3
