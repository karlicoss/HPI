from pathlib import Path
from typing import List, Dict, NamedTuple
from datetime import datetime

from xml.dom.minidom import parseString # type: ignore

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
            xmls.append(parseString(xx + _SP))
    return xmls


def get_books():
    books = []
    for review in get_reviews():
        book_element = review.getElementsByTagName('book')[0]
        title_element = book_element.getElementsByTagName('title')[0]
        id_element = book_element.getElementsByTagName('id')[0]
        isbn_element = book_element.getElementsByTagName('isbn')[0]
        isbn13_element = book_element.getElementsByTagName('isbn13')[0]
        date_added = review.getElementsByTagName('date_added')[0]
        started_at = review.getElementsByTagName('started_at')[0]
        read_at = review.getElementsByTagName('read_at')[0]

        shelves_element = review.getElementsByTagName('shelves')[0]
        book_shelves = []
        for shelf in shelves_element.getElementsByTagName('shelf'):
            book_shelves.append(shelf.getAttribute('name'))

        book = {
            'title': title_element.firstChild.data,
            'id': id_element.firstChild.data,
            'shelves': book_shelves
        }

        if isbn_element.getAttribute('nil') != 'true':
            book['isbn'] = isbn_element.firstChild.data
        else:
            book['isbn'] = ''

        if isbn13_element.getAttribute('nil') != 'true':
            book['isbn13'] = isbn13_element.firstChild.data
        else:
            book['isbn13'] = ''

        if started_at.firstChild is not None:
            book['started_at'] = started_at.firstChild.data
        else:
            book['started_at'] = ''

        if read_at.firstChild is not None:
            book['read_at'] = read_at.firstChild.data
        else:
            book['read_at'] = ''

        book['date_added'] = None if date_added.firstChild is None else date_added.firstChild.data

        books.append(book)
    return books


class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")


def get_events():
    events = []
    for b in get_books():
        added = _parse_date(b['date_added'])
        title = b['title']
        events.append(Event(
            dt=added,
            summary=f'Added book "{title}"', # TODO shelf?
            eid=b['id'],
        ))
        # TODO finished? other updates?
    return sorted(events, key=lambda e: e.dt)


def test():
    assert len(get_events()) > 20
