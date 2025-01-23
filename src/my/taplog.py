'''
[[https://play.google.com/store/apps/details?id=com.waterbear.taglog][Taplog]] app data
'''
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import NamedTuple

from my.config import taplog as user_config
from my.core import Stats, get_files, stat
from my.core.sqlite import sqlite_connection


class Entry(NamedTuple):
    row: dict

    @property
    def id(self) -> str:
        return str(self.row['_id'])

    @property
    def number(self) -> float | None:
        ns = self.row['number']
        # TODO ??
        if isinstance(ns, str):
            ns = ns.strip()
            return None if len(ns) == 0 else float(ns)
        else:
            return ns

    @property
    def note(self) -> str:
        return self.row['note']

    @property
    def button(self) -> str:
        return self.row['cat1']

    @property
    def timestamp(self) -> datetime:
        ts = self.row['timestamp']
        # already with timezone apparently
        # TODO not sure if should still localize though? it only kept tz offset, not real tz
        return datetime.fromisoformat(ts)
    # TODO also has gps info!


def entries() -> Iterable[Entry]:
    last = max(get_files(user_config.export_path))
    with sqlite_connection(last, immutable=True, row_factory='dict') as db:
        # todo is it sorted by timestamp?
        for row in db.execute('SELECT * FROM Log'):
            yield Entry(row)


# I guess worth having as top level considering it would be quite common?
def by_button(button: str) -> Iterable[Entry]:
    for e in entries():
        if e.button == button:
            yield e


def stats() -> Stats:
    return stat(entries)
