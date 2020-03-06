import os
from pathlib import Path
from typing import Dict, List, NamedTuple, Iterator, Iterable
from datetime import datetime
import pytz

from lxml import etree # type: ignore

BPATH = Path("/L/backups/smscalls")


class Call(NamedTuple):
    dt: datetime
    duration_s: int
    who: str

    @property
    def summary(self) -> str:
        return f"talked with {self.who} for {self.duration_s} secs"


def _extract_calls(fname: str) -> Iterator[Call]:
    tr = etree.parse(fname)
    for cxml in tr.findall('call'):
        # TODO we've got local tz herer, not sure if useful..
        # ok, so readable date is local datetime, cahnging throughout the backup
        dt = pytz.utc.localize(datetime.utcfromtimestamp(int(cxml.get('date')) / 1000))
        yield Call(
            dt=dt,
            duration_s=int(cxml.get('duration')),
            who=cxml.get('contact_name') # TODO number if contact is unavail??
            # TODO type? must be missing/outgoing/incoming
        )

def get_calls():
    calls: Dict[datetime, Call] = {}
    for n in sorted(BPATH.glob('calls-*.xml')):
        # for c in _extract_calls(os.path.join(BPATH, n)):
        #     cc = calls.get(c.dt, None)
        #     if cc is not None and cc != c:
        #         print(f"WARNING: {cc} vs {c}")
        calls.update({c.dt: c for c in _extract_calls(os.path.join(BPATH, n))})
        # always replacing with latter is good, we get better contact names
    return sorted(calls.values(), key=lambda c: c.dt)


def test():
    assert len(get_calls()) > 10
