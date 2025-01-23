"""
[[https://uk.kobobooks.com/products/kobo-aura-one][Kobo]] e-ink reader: annotations and reading stats
"""
from __future__ import annotations

REQUIRES = [
    'kobuddy',
]

from collections.abc import Iterator
from dataclasses import dataclass

import kobuddy
from kobuddy import *
from kobuddy import Highlight, get_highlights

from my.core import (
    Paths,
    Stats,
    get_files,
    stat,
)
from my.core.cfg import make_config

import my.config  # isort: skip


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


from typing import Callable, Union

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


def by_annotation(predicatish: Predicatish, **kwargs) -> list[Highlight]:
    pred = from_predicatish(predicatish)

    res: list[Highlight] = []
    for h in get_highlights(**kwargs):
        if pred(h.annotation):
            res.append(h)
    return res


def get_todos() -> list[Highlight]:
    def with_todo(ann):
        if ann is None:
            ann = ''
        return 'todo' in ann.lower().split()

    return by_annotation(with_todo)


def test_todos() -> None:
    todos = get_todos()
    assert len(todos) > 3
