#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple
from pathlib import Path
import json
from typing import Dict, Iterator, Any

from kython import cproperty, fget
from kython.konsume import dell, zoom, keq, akeq
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
    json: Dict[str, Any]
    cmap: Cmap

    @cproperty
    def uid(self) -> str:
        return self.contest_id

    @property
    def contest_id(self):
        return self.json['contestId']

    def __hash__(self):
        return hash(self.contest_id)

    @cproperty
    def when(self) -> datetime:
        return self.cmap[self.uid].when

    @cproperty
    def contest(self) -> str:
        return self.json['contestName']

    @cproperty
    def summary(self) -> str:
        return f'participated in {self.contest}' # TODO 

    @classmethod
    def make(cls, cmap, json) -> Iterator[Res['Competition']]:
        yield cls(cmap=cmap, json=json)
        yield from ytry(lambda: akeq(json, 'contestId', 'contestName', 'rank', 'oldRating', 'newRating'))


def iter_data() -> Iterator[Res[Competition]]:
    cmap = get_contests()

    j = get_latest()
    dell(j, 'status')

    j = zoom(j, 'result')

    for c in j:
        dell(c, 'handle', 'ratingUpdateTimeSeconds')
        yield from Competition.make(cmap=cmap, json=c)


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
