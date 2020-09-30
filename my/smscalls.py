"""
Phone calls and SMS messages
"""
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Iterator, Set, Tuple

import pytz
from lxml import etree # type: ignore

from .core.common import get_files

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
        # TODO we've got local tz here, not sure if useful..
        # ok, so readable date is local datetime, changing throughout the backup
        yield Call(
            dt=_parse_dt_ms(cxml.get('date')),
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


class Message(NamedTuple):
    dt: datetime
    who: str
    message: str
    phone_number: str
    from_me: bool


def messages() -> Iterator[Message]:
    files = get_files(config.export_path, glob='sms-*.xml')

    emitted: Set[Tuple[datetime, str, bool]] = set()
    for p in files:
        for c in _extract_messages(p):
            key = (c.dt, c.who, c.from_me)
            if key in emitted:
                continue
            emitted.add(key)
            yield c


def _extract_messages(path: Path) -> Iterator[Message]:
    tr = etree.parse(str(path))
    for mxml in tr.findall('sms'):
        yield Message(
            dt=_parse_dt_ms(mxml.get('date')),
            who=mxml.get('contact_name'),
            message=mxml.get('body'),
            phone_number=mxml.get('address'),
            from_me=mxml.get('type') == '2',  # 1 is received message, 2 is sent message
        )

def _parse_dt_ms(d: str) -> datetime:
    return pytz.utc.localize(datetime.utcfromtimestamp(int(d) / 1000))


def stats():
    from .core import stat

    return {
        **stat(calls),
        **stat(messages),
    }
