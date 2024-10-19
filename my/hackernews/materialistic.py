"""
[[https://play.google.com/store/apps/details?id=io.github.hidroh.materialistic][Materialistic]] app for Hackernews
"""
from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

from more_itertools import unique_everseen

from my.core import datetime_aware, get_files, make_logger
from my.core.sqlite import sqlite_connection

from .common import hackernews_link

# todo migrate config to my.hackernews.materialistic
from my.config import materialistic as config  # isort: skip

logger = make_logger(__name__)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


Row = dict[str, Any]


class Saved(NamedTuple):
    row: Row

    # NOTE: seems like it's the time item was saved (not created originally??)
    # https://github.com/hidroh/materialistic/blob/b631d5111b7487d2328f463bd95e8507c74c3566/app/src/main/java/io/github/hidroh/materialistic/data/MaterialisticDatabase.java#L224
    # but not 100% sure.
    @property
    def when(self) -> datetime_aware:
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


def _all_raw() -> Iterator[Row]:
    paths = inputs()
    total = len(paths)
    width = len(str(total))
    for idx, path in enumerate(paths):
        logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
        with sqlite_connection(path, immutable=True, row_factory='dict') as conn:
            yield from conn.execute('SELECT * FROM saved ORDER BY time')


def raw() -> Iterator[Row]:
    yield from unique_everseen(_all_raw(), key=lambda r: r['itemid'])


def saves() -> Iterator[Saved]:
    yield from map(Saved, raw())
