"""
[[https://play.google.com/store/apps/details?id=io.github.hidroh.materialistic][Materialistic]] app for Hackernews
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, NamedTuple, Sequence

from my.core import get_files
from my.core.sqlite import sqlite_connection

from my.config import materialistic as config
# todo migrate config to my.hackernews.materialistic


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


Row = Dict[str, Any]
from .common import hackernews_link

class Saved(NamedTuple):
    row: Row

    @property
    def when(self) -> datetime:
        ts = int(self.row['time']) / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    @property
    def uid(self) -> str:
        return self.row['itemid']

    @property
    def url(self) -> str:
        return self.row['url']

    @property
    def title(self) -> str:
        return self.row['title']

    @property
    def hackernews_link(self) -> str:
        return hackernews_link(self.uid)


def raw() -> Iterator[Row]:
    last = max(inputs())
    with sqlite_connection(last, immutable=True, row_factory='dict') as conn:
        yield from conn.execute('SELECT * FROM saved ORDER BY time')
        # TODO wonder if it's 'save time' or creation time?


def saves() -> Iterator[Saved]:
    yield from map(Saved, raw())
