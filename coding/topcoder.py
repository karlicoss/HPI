#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple
from pathlib import Path
import json
from typing import Dict, Iterator, Any

from kython import cproperty, fget
from kython.konsume import dell, zoom, keq, akeq
from kython.kerror import Res, ytry, unwrap


def get_latest():
    last = max(Path('/L/Dropbox/data/topcoder').glob('*.json'))
    return json.loads(last.read_text())


class Competition(NamedTuple):
    json: Dict[str, Any]

    @cproperty
    def uid(self) -> str:
        return self.contest

    def __hash__(self):
        return hash(self.json['challengeId'])

    @cproperty
    def contest(self) -> str:
        return self.json['challengeName']

    @cproperty
    def when(self) -> datetime:
        ds =  self.json['date']
        return datetime.strptime(ds, '%Y-%m-%dT%H:%M:%S.%fZ')

    @cproperty
    def percentile(self) -> float:
        return self.json['percentile']

    @cproperty
    def summary(self) -> str:
        return f'participated in {self.contest}: {self.percentile:.0f}'

    @classmethod
    def make(cls, json) -> Iterator[Res['Competition']]:
        yield cls(json=json)
        yield from ytry(lambda: akeq(json, 'challengeId', 'challengeName', 'percentile', 'rating', 'placement', 'date'))


def iter_data() -> Iterator[Res[Competition]]:
    j = get_latest()
    dell(j, 'id', 'version')

    j = zoom(j, 'result')
    dell(j, 'success', 'status', 'metadata')

    j = zoom(j, 'content')

    dell(j, 'handle', 'handleLower', 'userId', 'createdAt', 'updatedAt', 'createdBy', 'updatedBy')

    dell(j, 'DEVELOP') # TODO handle it??
    j = zoom(j, 'DATA_SCIENCE')

    mar, srm = zoom(j, 'MARATHON_MATCH', 'SRM')

    mar = zoom(mar, 'history')
    srm = zoom(srm, 'history')
    # TODO right, I guess I could rely on pylint for unused variables??

    for c in mar + srm:
        yield from Competition.make(json=c)


def get_data():
    return list(sorted(iter_data(), key=fget(Competition.when)))


def main():
    for d in iter_data():
        try:
            d = unwrap(d)
            print(d.summary)
        except Exception as e:
            print(f'ERROR! {d}')


if __name__ == '__main__':
    main()
