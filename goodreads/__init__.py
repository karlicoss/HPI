#!/usr/bin/env python3
from pathlib import Path
from typing import List, Dict, NamedTuple, Iterator, Optional, Sequence
from datetime import datetime
import pytz

from lxml import etree as ET # type: ignore

BPATH = Path("/L/backups/goodreads")

# TODO might be useful to keep track of updates?...
# then I need some sort of system to store diffs in generic way...
# althogh... coud use same mechanism as for filtering
def get_last() -> Path:
    return max(sorted(BPATH.glob('*.xmll')))

_SP = '</review>'

def get_reviews():
    fname = get_last()
    xmls = []
    with open(fname, 'r') as fo:
        data = fo.read()
        for xx in data.split(_SP):
            if len(xx.strip()) == 0:
                break
            xmls.append(ET.fromstring(xx + _SP))
    return xmls

class Book(NamedTuple):
    bid: str
    title: str
    authors: Sequence[str]
    shelves: Sequence[str]
    date_added: datetime
    date_started: Optional[datetime]
    date_read: Optional[datetime]

from kython import the


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    res = datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
    assert res.tzinfo is not None
    return res


def iter_books() -> Iterator[Book]:
    for r in get_reviews():
        # review_xml = the(review.childNodes)
        # rdict = {n.tagName: n for n in review_xml.childNodes if isinstance(n, Element)}
        # fuck xml...

        be    = the(r.xpath('book'))
        title = the(be.xpath('title/text()'))
        authors = be.xpath('authors/author/name/text()')

        bid     = the(r.xpath('id/text()'))
        # isbn_element   = the(book_element.getElementsByTagName('isbn'))
        # isbn13_element = the(book_element.getElementsByTagName('isbn13'))
        date_added     = the(r.xpath('date_added/text()'))
        sss = r.xpath('started_at/text()')
        rrr = r.xpath('read_at/text()')
        started_at     = None if len(sss) == 0 else the(sss)
        read_at        = None if len(rrr) == 0 else the(rrr)

        shelves = r.xpath('shelves/shelf/name/text()')

        # if isbn_element.getAttribute('nil') != 'true':
        #     book['isbn'] = isbn_element.firstChild.data
        # else:
        #     book['isbn'] = ''

        # if isbn13_element.getAttribute('nil') != 'true':
        #     book['isbn13'] = isbn13_element.firstChild.data
        # else:
        #     book['isbn13'] = ''

        da = _parse_date(date_added)
        assert da is not None
        yield Book(
            bid=bid,
            title=title,
            authors=authors,
            shelves=shelves,
            date_added=da,
            date_started=_parse_date(started_at),
            date_read=_parse_date(read_at),
        )

def get_books():
    return list(iter_books())


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
            eid=b.bid
        ))
        # TODO finished? other updates?
    return sorted(events, key=lambda e: e.dt)


def test():
    assert len(get_events()) > 20


def print_read_history():
    def key(b):
        read = b.date_read
        if read is None:
            return datetime.fromtimestamp(0, pytz.utc)
        else:
            return read

    def fmtdt(dt):
        if dt is None:
            return dt
        tz = pytz.timezone('Europe/London')
        return dt.astimezone(tz)
    for b in sorted(iter_books(), key=key):
        print(f"""
{b.title} by {', '.join(b.authors)}
    started : {fmtdt(b.date_started)}
    finished: {fmtdt(b.date_read)}
        """)


def main():
    import argparse
    p = argparse.ArgumentParser()
    sp = p.add_argument('mode', nargs='?')
    args = p.parse_args()

    if args.mode == 'history':
        print_read_history()
    else:
        assert args.mode is None
        for b in iter_books():
            print(b)

if __name__ == '__main__':
    main()
