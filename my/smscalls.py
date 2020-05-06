"""
Phone calls and SMS messages
"""
# TODO extract SMS as well? I barely use them though..
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Iterator, Set

import pytz
from lxml import etree # type: ignore

from .common import get_files

from my.config import smscalls as config


class Call(NamedTuple):
    dt: datetime
    duration_s: int
    who: str

    @property
    def summary(self) -> str:
        return f"talked with {self.who} for {self.duration_s} secs"


def _extract_calls(path: Path) -> Iterator[Call]:
    tr = etree.parse(str(path))
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


def calls() -> Iterator[Call]:
    files = get_files(config.export_path, glob='calls-*.xml')

    # TODO always replacing with the latter is good, we get better contact names??
    emitted: Set[datetime] = set()
    for p in files:
        for c in _extract_calls(p):
            if c.dt in emitted:
                continue
            emitted.add(c.dt)
            yield c
