#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple, List
from pathlib import Path

from kython.ktakeout import TakeoutHTMLParser
from kython.kompress import open as kopen

from ..common import get_files

from my_configuration import paths


def _get_last_takeout():
    # TODO FIXME might be a good idea to merge across multiple taekouts...
    # perhaps even a special takeout module that deals with all of this automatically?
    # e.g. accumulate, filter and maybe report useless takeouts?
    return max(get_files(paths.google.takeout_path, glob='*.zip'))


class Watched(NamedTuple):
    url: str
    title: str
    when: datetime

    @property
    def eid(self) -> str:
        return f'{self.url}-{self.when.isoformat()}'


def get_watched():
    last = _get_last_takeout()

    watches: List[Watched] = []
    def cb(dt, url, title):
        watches.append(Watched(url=url, title=title, when=dt))

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
