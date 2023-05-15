"""
Phone calls and SMS messages
Exported using https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore&hl=en_US
"""

# See: https://www.synctech.com.au/sms-backup-restore/fields-in-xml-backup-files/ for schema

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
from typing import NamedTuple, Iterator, Set, Tuple, Optional

from lxml import etree

from my.core.common import get_files, Stats
from my.core.error import Res


class Call(NamedTuple):
    dt: datetime
    dt_readable: str
    duration_s: int
    who: Optional[str]
    # type - 1 = Incoming, 2 = Outgoing, 3 = Missed, 4 = Voicemail, 5 = Rejected, 6 = Refused List.
    call_type: int

    @property
    def summary(self) -> str:
        return f"talked with {self.who} for {self.duration_s} secs"

    @property
    def from_me(self) -> bool:
        return self.call_type == 2


# From docs:
# All the field values are read as-is from the underlying database and no conversion is done by the app in most cases.
#
# The '(Unknown)' is just what my android phone does, not sure if there are others
UNKNOWN: Set[str] = {'(Unknown)'}


def _extract_calls(path: Path) -> Iterator[Res[Call]]:
    tr = etree.parse(str(path))
    for cxml in tr.findall('call'):
        dt = cxml.get('date')
        dt_readable = cxml.get('readable_date')
        duration = cxml.get('duration')
        who = cxml.get('contact_name')
        call_type = cxml.get('type')
        # if name is missing, its not None (its some string), depends on the phone/message app
        if who is not None and who in UNKNOWN:
            who = None
        if dt is None or dt_readable is None or duration is None or call_type is None:
            call_str = etree.tostring(cxml).decode('utf-8')
            yield RuntimeError(f"Missing one or more required attributes [date, readable_date, duration, type] in {call_str}")
            continue
        # TODO we've got local tz here, not sure if useful..
        # ok, so readable date is local datetime, changing throughout the backup
        yield Call(
            dt=_parse_dt_ms(dt),
            dt_readable=dt_readable,
            duration_s=int(duration),
            who=who,
            call_type=int(call_type),
        )


def calls() -> Iterator[Res[Call]]:
    files = get_files(config.export_path, glob='calls-*.xml')

    # TODO always replacing with the latter is good, we get better contact names??
    emitted: Set[datetime] = set()
    for p in files:
        for c in _extract_calls(p):
            if isinstance(c, Exception):
                yield c
                continue
            if c.dt in emitted:
                continue
            emitted.add(c.dt)
            yield c


class Message(NamedTuple):
    dt: datetime
    dt_readable: str
    who: Optional[str]
    message: str
    phone_number: str
    # type - 1 = Received, 2 = Sent, 3 = Draft, 4 = Outbox, 5 = Failed, 6 = Queued
    message_type: int

    @property
    def from_me(self) -> bool:
        return self.message_type == 2


def messages() -> Iterator[Res[Message]]:
    files = get_files(config.export_path, glob='sms-*.xml')

    emitted: Set[Tuple[datetime, Optional[str], bool]] = set()
    for p in files:
        for c in _extract_messages(p):
            if isinstance(c, Exception):
                yield c
                continue
            key = (c.dt, c.who, c.from_me)
            if key in emitted:
                continue
            emitted.add(key)
            yield c


def _extract_messages(path: Path) -> Iterator[Res[Message]]:
    tr = etree.parse(str(path))
    for mxml in tr.findall('sms'):
        dt = mxml.get('date')
        dt_readable = mxml.get('readable_date')
        who = mxml.get('contact_name')
        if who is not None and who in UNKNOWN:
            who = None
        message = mxml.get('body')
        phone_number = mxml.get('address')
        message_type = mxml.get('type')

        if dt is None or dt_readable is None or message is None or phone_number is None or message_type is None:
            msg_str = etree.tostring(mxml).decode('utf-8')
            yield RuntimeError(f"Missing one or more required attributes [date, readable_date, body, address, type] in {msg_str}")
            continue
        yield Message(
            dt=_parse_dt_ms(dt),
            dt_readable=dt_readable,
            who=who,
            message=message,
            phone_number=phone_number,
            message_type=int(message_type),
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
