#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple, List
from pathlib import Path

from kython.ktakeout import TakeoutHTMLParser
from kython.kompress import open as kopen

BDIR = Path("/L/backups/takeout/karlicoss_gmail_com/")

class Watched(NamedTuple):
    url: str
    # TODO title
    when: datetime

    @property
    def eid(self) -> str:
        return f'{self.url}-{self.when.isoformat()}'

def get_watched():
    last = max(BDIR.glob('*.zip'))

    watches: List[Watched] = []
    def cb(dt, url):
        watches.append(Watched(url=url, when=dt))

    parser = TakeoutHTMLParser(cb)

    with kopen(last, 'Takeout/My Activity/YouTube/MyActivity.html') as fo:
        dd = fo.read().decode('utf8')
        parser.feed(dd)

    return list(sorted(watches, key=lambda e: e.when))


def test():
    watched = get_watched()
    assert len(watched) > 1000


def main():
    # TODO shit. a LOT of watches...
    for w in get_watched():
        print(w)

if __name__ == '__main__':
    main()
