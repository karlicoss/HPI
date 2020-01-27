"""
Module for Materialistic app for Hackernews
https://play.google.com/store/apps/details?id=io.github.hidroh.materialistic
"""

from datetime import datetime
from typing import Any, Dict, Iterator, NamedTuple

import pytz
import dataset # type: ignore

from mycfg import paths


Row = Dict[str, Any]

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
        return f'https://news.ycombinator.com/item?id={self.uid}'


def raw() -> Iterator[Row]:
    db = dataset.connect('sqlite:///' + str(max(paths.materialistic.export_path.glob('*.db'))))
    st = db['saved']
    # TODO wonder if it's 'save time'?
    yield from st.all(order_by='time')


def saves() -> Iterator[Saved]:
    yield from map(Saved, raw())
