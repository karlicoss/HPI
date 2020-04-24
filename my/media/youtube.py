#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple, List

# TODO ugh. reuse it in mypkg/releaste takeout parser separately?
from ..kython.ktakeout import TakeoutHTMLParser

from ..kython.kompress import kopen
from ..takeout import get_last_takeout


class Watched(NamedTuple):
    url: str
    title: str
    when: datetime

    @property
    def eid(self) -> str:
        return f'{self.url}-{self.when.isoformat()}'


def get_watched():
    # TODO need to use a glob? to make up for old takouts that didn't start with Takeout/
    path = 'Takeout/My Activity/YouTube/MyActivity.html' # looks like this one doesn't have retention? so enough to use the last
    # TODO YouTube/history/watch-history.html, also YouTube/history/watch-history.json
    last = get_last_takeout(path=path)

    watches: List[Watched] = []
    def cb(dt, url, title):
        watches.append(Watched(url=url, title=title, when=dt))

    parser = TakeoutHTMLParser(cb)

    with kopen(last, path) as fo:
        dd = fo.read().decode('utf8')
        parser.feed(dd)

    # TODO hmm they already come sorted.. wonder if should just rely on it..
    return list(sorted(watches, key=lambda e: e.when))


def main():
    # TODO shit. a LOT of watches...
    for w in get_watched():
        print(w)

if __name__ == '__main__':
    main()
