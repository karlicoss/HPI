"""
[[https://play.google.com/store/apps/details?id=io.github.hidroh.materialistic][Materialistic]] app for Hackernews
"""

REQUIRES = ['hpikit', 'kloggy', 'koncurrent']

from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

import koncurrent
from hpikit.datetime import AwareDateTime, aware
from hpikit.paths import get_files
from kloggy import get_logger
from kloggy.progress import progress
from more_itertools import unique_everseen

from my.core.sqlite import sqlite_connection

from .common import hackernews_link

# todo migrate config to my.hackernews.materialistic
from my.config import materialistic as config  # isort: skip

logger = get_logger(__name__)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


Row = dict[str, Any]


class Saved(NamedTuple):
    row: Row

    # Timestamp evidence: the pinned upstream SavedStory.from writes System.currentTimeMillis() to time.
    # https://github.com/hidroh/materialistic/blob/b631d5111b7487d2328f463bd95e8507c74c3566/app/src/main/java/io/github/hidroh/materialistic/data/MaterialisticDatabase.java#L210-L230
    # https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/System.html#currentTimeMillis()
    @property
    def when(self) -> AwareDateTime:
        """
        NOTE: this is the time the item was saved, not the Hacker News item's creation time.
        """
        ts = int(self.row['time']) / 1000
        return aware(datetime.fromtimestamp(ts, tz=UTC))

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


def _process_path(path: Path) -> list[Row]:
    with sqlite_connection(path, immutable=True, row_factory='dict') as conn:
        return list(conn.execute('SELECT * FROM saved ORDER BY time'))


def _all_raw() -> Iterator[Row]:
    paths = inputs()
    with koncurrent.map_results(_process_path, paths) as results:
        files = progress(paths, logger=logger, unit='files')
        for path, result in zip(files, results, strict=True):
            if isinstance(result, Exception):
                result.add_note(f'^ while processing {path}')
                raise result
            yield from result


def raw() -> Iterator[Row]:
    yield from unique_everseen(_all_raw(), key=lambda r: r['itemid'])


def saves() -> Iterator[Saved]:
    yield from map(Saved, raw())
