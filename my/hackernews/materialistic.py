"""
[[https://play.google.com/store/apps/details?id=io.github.hidroh.materialistic][Materialistic]] app for Hackernews
"""

REQUIRES = ['dataset']

from datetime import datetime
from typing import Any, Dict, Iterator, NamedTuple, Sequence

import pytz

from my.config import materialistic as config
# todo migrate config to my.hackernews.materialistic


from ..core import get_files
from pathlib import Path
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


Row = Dict[str, Any]
from .common import hackernews_link

class Saved(NamedTuple):
    row: Row

    @property
    def when(self) -> datetime:
        ts = int(self.row['time']) / 1000
        return datetime.fromtimestamp(ts, tz=pytz.utc)

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


from ..core.dataset import connect_readonly
def raw() -> Iterator[Row]:
    last = max(inputs())
    with connect_readonly(last) as db:
        saved = db['saved']
        # TODO wonder if it's 'save time' or creation time?
        yield from saved.all(order_by='time')


def saves() -> Iterator[Saved]:
    yield from map(Saved, raw())
