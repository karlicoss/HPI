"""
Phone calls and SMS messages
Exported using https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore&hl=en_US
"""

REQUIRES = ['lxml']

from .core import Paths, dataclass
from my.config import smscalls as user_config

@dataclass
class smscalls(user_config):
    # path[s] that SMSBackupRestore syncs XML files to
    export_path: Paths

from .core.cfg import make_config
config = make_config(smscalls)

from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple, Iterator, Set, Tuple

from lxml import etree # type: ignore

from .core.common import get_files, Stats


class Call(NamedTuple):
    dt: datetime
    dt_readable: str
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
            dt_readable=cxml.get('readable_date'),
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
    dt_readable: str
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
            dt_readable=mxml.get('readable_date'),
            who=mxml.get('contact_name'),
            message=mxml.get('body'),
            phone_number=mxml.get('address'),
            from_me=mxml.get('type') == '2',  # 1 is received message, 2 is sent message
        )


# See https://github.com/karlicoss/HPI/pull/90#issuecomment-702422351
# for potentially parsing timezone from the readable_date
def _parse_dt_ms(d: str) -> datetime:
    return datetime.fromtimestamp(int(d) / 1000, tz=timezone.utc)


def stats() -> Stats:
    from .core import stat

    return {
        **stat(calls),
        **stat(messages),
    }
