#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple
from pathlib import Path
import json
from typing import Dict, Iterator, Any

from kython import cproperty, fget
from kython.konsume import zoom, ignore
from kython.kerror import Res, ytry, unwrap
from kython.kdatetime import as_utc


_BDIR = Path('/L/Dropbox/data/codeforces')


Cid = int

class Contest(NamedTuple):
    cid: Cid
    when: datetime

    @classmethod
    def make(cls, j) -> 'Contest':
        return cls(
            cid=j['id'],
            when=as_utc(j['startTimeSeconds']),
        )

Cmap = Dict[Cid, Contest]

def get_contests() -> Cmap:
    last = max(_BDIR.glob('allcontests*.json'))
    j = json.loads(last.read_text())
    d = {}
    for c in j['result']:
        cc = Contest.make(c)
        d[cc.cid] = cc
    return d


def get_latest():
    last = max(_BDIR.glob('codeforces*.json'))
    return json.loads(last.read_text())


class Competition(NamedTuple):
    contest_id: str
    contest: str
    cmap: Cmap

    @cproperty
    def uid(self) -> str:
        return self.contest_id

    def __hash__(self):
        return hash(self.contest_id)

    @cproperty
    def when(self) -> datetime:
        return self.cmap[self.uid].when

    @cproperty
    def summary(self) -> str:
        return f'participated in {self.contest}' # TODO 

    @classmethod
    def make(cls, cmap, json) -> Iterator[Res['Competition']]:
        # TODO try here??
        contest_id = json['contestId'].zoom().value
        contest = json['contestName'].zoom().value
        yield cls(
            contest_id=contest_id,
            contest=contest,
            cmap=cmap,
        )
        # TODO ytry???
        ignore(json, 'rank', 'oldRating', 'newRating')

from kython.konsume import wrap
def iter_data() -> Iterator[Res[Competition]]:
    cmap = get_contests()

    with wrap(get_latest()) as j:
        j['status'].ignore()
        res = j['result'].zoom()

        for c in list(res): # TODO maybe we want 'iter' method??
            ignore(c, 'handle', 'ratingUpdateTimeSeconds')
            yield from Competition.make(cmap=cmap, json=c)
            c.consume()
            # TODO maybe if they are all empty, no need to consume??


def get_data():
    return list(sorted(iter_data(), key=fget(Competition.when)))

def main():
    for d in iter_data():
        try:
            d = unwrap(d)
        except Exception as e:
            print(f'ERROR! {d}')
        else:
            print(f'{d.when}: {d.summary}')



if __name__ == '__main__':
    main()
