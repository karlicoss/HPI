"""
[[https://www.goodreads.com][Goodreads]] statistics
"""
REQUIRES = [
    'git+https://github.com/karlicoss/goodrexport',
]


from dataclasses import dataclass
from my.core import Paths
from my.config import goodreads as user_config

@dataclass
class goodreads(user_config):
    # paths[s]/glob to the exported JSON data
    export_path: Paths

from my.core.cfg import make_config, Attrs

def _migration(attrs: Attrs) -> Attrs:
    export_dir = 'export_dir'
    if export_dir in attrs: # legacy name
        attrs['export_path'] = attrs[export_dir]
        from my.core.warnings import high
        high(f'"{export_dir}" is deprecated! Please use "export_path" instead."')
    return attrs
config = make_config(goodreads, migration=_migration)

#############################3


from my.core import get_files
from typing import Sequence, Iterator
from pathlib import Path

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

from my.core.common import datetime_aware
@dataclass
class Event:
    dt: datetime_aware
    summary: str
    eid: str


def events() -> Iterator[Event]:
    for b in books():
        yield Event(
            dt=b.date_added,
            summary=f'Added book "{b.title}"', # todo shelf?
            eid=b.id
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
