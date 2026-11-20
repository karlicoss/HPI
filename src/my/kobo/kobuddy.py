"""
[[https://uk.kobobooks.com/products/kobo-aura-one][Kobo]] e-ink reader: annotations and reading stats

Reads Kobo database backups with [[https://github.com/karlicoss/kobuddy#as-a-backup-tool][kobuddy]].
"""

from __future__ import annotations

REQUIRES = [
    'kobuddy',
]

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import cast

import kobuddy
from kobuddy import *
from kobuddy import Highlight, get_highlights

from my.core import Paths, Stats, get_files, stat, warnings


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to Kobo SQLite database backups."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import kobo as user_config

    if hasattr(user_config, 'kobuddy'):

        class combined_config(user_config.kobuddy, Config):
            pass

        return combined_config()

    warnings.high('The flat Kobo config is deprecated. Use my.config.kobo.kobuddy.export_path instead.')
    return cast(Config, user_config())


# All kobuddy readers, including the ones re-exported above, use this shared database list.
# TODO Give kobuddy a DAL that accepts the database paths explicitly.
kobuddy.DATABASES = list(get_files(make_config().export_path))


def highlights() -> Iterator[Highlight]:
    return kobuddy._iter_highlights()


def stats() -> Stats:
    return stat(highlights)


## TODO hmm. not sure if all this really belongs here?... perhaps orger?


# TODO maybe type over T?
_Predicate = Callable[[str], bool]
Predicatish = str | _Predicate


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
