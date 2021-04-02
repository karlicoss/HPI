#!/usr/bin/env python3
from my.config import codeforces as config

from datetime import datetime
from typing import NamedTuple
import json
from typing import Dict, Iterator

from ..common import cproperty, get_files
from ..error import Res, unwrap
from ..core.konsume import ignore, wrap

from kython import fget
# TODO remove
from kython.kdatetime import as_utc


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
    last = max(get_files(config.export_path, 'allcontests*.json'))
    j = json.loads(last.read_text())
    d = {}
    for c in j['result']:
        cc = Contest.make(c)
        d[cc.cid] = cc
    return d


class Competition(NamedTuple):
    contest_id: Cid
    contest: str
    cmap: Cmap

    @cproperty
    def uid(self) -> Cid:
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


def iter_data() -> Iterator[Res[Competition]]:
    cmap = get_contests()
    last = max(get_files(config.export_path, 'codeforces*.json'))

    with wrap(json.loads(last.read_text())) as j:
        j['status'].ignore()
        res = j['result'].zoom()

        for c in list(res): # TODO maybe we want 'iter' method??
            ignore(c, 'handle', 'ratingUpdateTimeSeconds')
            yield from Competition.make(cmap=cmap, json=c)
            c.consume()
            # TODO maybe if they are all empty, no need to consume??


def get_data():
    return list(sorted(iter_data(), key=fget(Competition.when)))


def test():
    assert len(get_data()) > 10


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
