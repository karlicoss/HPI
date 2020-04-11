#!/usr/bin/env python3
from functools import lru_cache
from typing import NamedTuple
from datetime import datetime
import pytz

from my.config.repos.goodrexport import dal as goodrexport
from my.config import goodreads as config


def get_model():
    sources = list(sorted(config.export_dir.glob('*.xml')))
    model = goodrexport.DAL(sources)
    return model


def get_books():
    model = get_model()
    return [r.book for r in model.reviews()]


def test_books():
    books = get_books()
    assert len(books) > 10


class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str


def get_events():
    events = []
    for b in get_books():
        events.append(Event(
            dt=b.date_added,
            summary=f'Added book "{b.title}"', # TODO shelf?
            eid=b.id
        ))
        # TODO finished? other updates?
    return sorted(events, key=lambda e: e.dt)


def print_read_history():
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
    for b in sorted(get_books(), key=key):
        print(f"""
{b.title} by {', '.join(b.authors)}
    started : {fmtdt(b.date_started)}
    finished: {fmtdt(b.date_read)}
        """)

def test():
    assert len(get_events()) > 20


# def main():
#     import argparse
#     p = argparse.ArgumentParser()
#     sp = p.add_argument('mode', nargs='?')
#     args = p.parse_args()

#     if args.mode == 'history':
#         print_read_history()
#     else:
#         assert args.mode is None
#         for b in iter_books():
#             print(b)

# if __name__ == '__main__':
#     main()
