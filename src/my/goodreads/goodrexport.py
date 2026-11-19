"""
[[https://www.goodreads.com][Goodreads]] books and reviews from [[https://github.com/karlicoss/goodrexport][goodrexport]] XML exports.
"""

REQUIRES = [
    'goodrexport @ git+https://github.com/karlicoss/goodrexport',
]


from dataclasses import dataclass

from my.config import goodreads as user_config
from my.core import Paths, datetime_aware, warnings


@dataclass
class goodreads(user_config):
    # Paths or globs pointing to Goodreads XML exports.
    export_path: Paths


from my.core.cfg import Attrs, make_config


def _migration(attrs: Attrs) -> Attrs:
    if 'export_dir' in attrs:
        old_name = 'export_dir'
        attrs['export_path'] = attrs['export_dir']
    elif 'export_path' in attrs:
        old_name = 'export_path'
    else:
        return attrs
    warnings.high(
        f'my.config.goodreads.{old_name} is deprecated. Use my.config.goodreads.goodrexport.export_path instead.'
    )
    return attrs


config = (
    user_config.goodrexport() if hasattr(user_config, 'goodrexport') else make_config(goodreads, migration=_migration)
)

#############################3


from collections.abc import Iterator, Sequence
from pathlib import Path

from my.core import get_files


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


from datetime import datetime

import pytz
from goodrexport import dal


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
