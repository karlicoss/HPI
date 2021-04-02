#!/usr/bin/env python3
from my.config import topcoder as config

from datetime import datetime
from typing import NamedTuple
import json
from typing import Dict, Iterator

from ..common import cproperty, get_files
from ..error import Res, unwrap

# TODO get rid of fget?
from kython import fget
from ..core.konsume import zoom, wrap, ignore


# TODO json type??
def _get_latest() -> Dict:
    pp = max(get_files(config.export_path, glob='*.json'))
    return json.loads(pp.read_text())


class Competition(NamedTuple):
    contest_id: str
    contest: str
    percentile: float
    dates: str

    @cproperty
    def uid(self) -> str:
        return self.contest_id

    def __hash__(self):
        return hash(self.contest_id)

    @cproperty
    def when(self) -> datetime:
        return datetime.strptime(self.dates, '%Y-%m-%dT%H:%M:%S.%fZ')

    @cproperty
    def summary(self) -> str:
        return f'participated in {self.contest}: {self.percentile:.0f}'

    @classmethod
    def make(cls, json) -> Iterator[Res['Competition']]:
        ignore(json, 'rating', 'placement')
        cid = json['challengeId'].zoom().value
        cname = json['challengeName'].zoom().value
        percentile = json['percentile'].zoom().value
        dates = json['date'].zoom().value
        yield cls(
            contest_id=cid,
            contest=cname,
            percentile=percentile,
            dates=dates,
        )


def iter_data() -> Iterator[Res[Competition]]:
    with wrap(_get_latest()) as j:
        ignore(j, 'id', 'version')

        res = j['result'].zoom()
        ignore(res, 'success', 'status', 'metadata')

        cont = res['content'].zoom()
        ignore(cont, 'handle', 'handleLower', 'userId', 'createdAt', 'updatedAt', 'createdBy', 'updatedBy')

        cont['DEVELOP'].ignore() # TODO handle it??
        ds = cont['DATA_SCIENCE'].zoom()

        mar, srm = zoom(ds, 'MARATHON_MATCH', 'SRM')

        mar = mar['history'].zoom()
        srm = srm['history'].zoom()
    # TODO right, I guess I could rely on pylint for unused variables??

        for c in mar + srm:
            yield from Competition.make(json=c)
            c.consume()


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
            print(d.summary)


if __name__ == '__main__':
    main()
