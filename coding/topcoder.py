#!/usr/bin/env python3
from datetime import datetime
from typing import NamedTuple
from pathlib import Path
import json
from typing import Dict, Iterator

from kython import cproperty
from kython.konsume import dell, zoom, keq, akeq
from kython.kerror import Res, ytry


def get_latest():
    last = max(Path('/L/Dropbox/data/topcoder').glob('*.json'))
    return json.loads(last.read_text())


class Competition(NamedTuple):
    json: Dict[str, str]

    @cproperty
    def contest(self) -> str:
        return self.json['challengeName']

    @cproperty
    def when(self) -> str:
        return self.json['date']

    # TODO rating/placement/percentile??

    @classmethod
    def make(cls, json) -> Iterator[Res['Competition']]:
        yield cls(json=json)
        yield from ytry(lambda: akeq(json, 'challengeName', 'percentile', 'rating', 'placement', 'date'))


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
        dell(c, 'challengeId')
        yield from Competition.make(json=c)


def get_data():
    return list(sorted(iter_data(), key=Competition.when))


def main():
    for d in iter_data():
        print(d)


if __name__ == '__main__':
    main()
