#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple, List, Iterable

from ..google.takeout.html import read_html
from ..google.takeout.paths import get_last_takeout


class Watched(NamedTuple):
    url: str
    title: str
    when: datetime

    @property
    def eid(self) -> str:
        return f'{self.url}-{self.when.isoformat()}'


def watched() -> Iterable[Watched]:
    # TODO need to use a glob? to make up for old takouts that didn't start with Takeout/
    path = 'Takeout/My Activity/YouTube/MyActivity.html' # looks like this one doesn't have retention? so enough to use the last
    # TODO YouTube/history/watch-history.html, also YouTube/history/watch-history.json
    last = get_last_takeout(path=path)
    if last is None:
        return []


    watches: List[Watched] = []
    for dt, url, title in read_html(last, path):
        watches.append(Watched(url=url, title=title, when=dt))

    # TODO hmm they already come sorted.. wonder if should just rely on it..
    return list(sorted(watches, key=lambda e: e.when))


from ..core import stat, Stats
def stats() -> Stats:
    return stat(watched)


# todo deprecate
get_watched = watched

