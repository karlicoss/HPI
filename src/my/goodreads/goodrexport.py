"""
[[https://www.goodreads.com][Goodreads]] books and reviews from [[https://github.com/karlicoss/goodrexport][goodrexport]] XML exports.
"""

REQUIRES = [
    'goodrexport @ git+https://github.com/karlicoss/goodrexport',
]

from abc import ABC, abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

import pytz
from goodrexport import dal

from my.core import Paths, datetime_aware, get_files, warnings


class Config(ABC):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """Paths or globs pointing to Goodreads XML exports."""
        raise NotImplementedError


def make_config() -> Config:
    from my.config import goodreads as user_config

    if hasattr(user_config, 'goodrexport'):

        class combined_config(user_config.goodrexport, Config):
            pass

        return combined_config()

    warnings.high('The flat Goodreads config is deprecated. Use my.config.goodreads.goodrexport.export_path instead.')
    return cast(Config, user_config())


def inputs() -> Sequence[Path]:
    return get_files(make_config().export_path)


def _dal() -> dal.DAL:
    return dal.DAL(inputs())


def reviews() -> Iterator[dal.Review]:
    return _dal().reviews()


# todo should be in DAL?
def books() -> Iterator[dal.Book]:
    for r in reviews():
        yield r.book


#######
# todo ok, not sure these really belong here...


@dataclass
class Event:
    dt: datetime_aware
    summary: str
    eid: str


def events() -> Iterator[Event]:
    for b in books():
        yield Event(
            dt=b.date_added,
            summary=f'Added book "{b.title}"',  # todo shelf?
            eid=b.id,
        )
    # todo finished? other updates?


def print_read_history() -> None:
    def ddate(x):
        if x is None:
            return datetime.fromtimestamp(0, pytz.utc)
        else:
            return x

    def key(b):
        return ddate(b.date_started)

    def fmtdt(dt):
        if dt is None:
            return dt
        tz = pytz.timezone('Europe/London')
        return dt.astimezone(tz)

    for b in sorted(books(), key=key):
        print(f"""
{b.title} by {', '.join(b.authors)}
    started : {fmtdt(b.date_started)}
    finished: {fmtdt(b.date_read)}
        """)
