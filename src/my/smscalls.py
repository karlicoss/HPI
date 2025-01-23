"""
Phone calls and SMS messages
Exported using https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore&hl=en_US
"""
from __future__ import annotations

# See: https://www.synctech.com.au/sms-backup-restore/fields-in-xml-backup-files/ for schema

REQUIRES = ['lxml']

from dataclasses import dataclass

from my.config import smscalls as user_config
from my.core import Paths, Stats, get_files, stat


@dataclass
class smscalls(user_config):
    # path[s] that SMSBackupRestore syncs XML files to
    export_path: Paths

from my.core.cfg import make_config

config = make_config(smscalls)

from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import lxml.etree as etree

from my.core.error import Res


class Call(NamedTuple):
    dt: datetime
    dt_readable: str
    duration_s: int
    phone_number: str
    who: str | None
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
UNKNOWN: set[str] = {'(Unknown)'}

def _parse_xml(xml: Path) -> Any:
    return etree.parse(str(xml), parser=etree.XMLParser(huge_tree=True))


def _extract_calls(path: Path) -> Iterator[Res[Call]]:
    tr = _parse_xml(path)
    for cxml in tr.findall('call'):
        dt = cxml.get('date')
        dt_readable = cxml.get('readable_date')
        duration = cxml.get('duration')
        who = cxml.get('contact_name')
        call_type = cxml.get('type')
        number = cxml.get('number')
        # if name is missing, its not None (its some string), depends on the phone/message app
        if who is not None and who in UNKNOWN:
            who = None
        if dt is None or dt_readable is None or duration is None or call_type is None or number is None:
            call_str = etree.tostring(cxml).decode('utf-8')
            yield RuntimeError(f"Missing one or more required attributes [date, readable_date, duration, type, number] in {call_str}")
            continue
        # TODO we've got local tz here, not sure if useful..
        # ok, so readable date is local datetime, changing throughout the backup
        yield Call(
            dt=_parse_dt_ms(dt),
            dt_readable=dt_readable,
            duration_s=int(duration),
            phone_number=number,
            who=who,
            call_type=int(call_type),
        )


def calls() -> Iterator[Res[Call]]:
    files = get_files(config.export_path, glob='calls-*.xml')

    # TODO always replacing with the latter is good, we get better contact names??
    emitted: set[datetime] = set()
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
    who: str | None
    message: str
    phone_number: str
    # type - 1 = Received, 2 = Sent, 3 = Draft, 4 = Outbox, 5 = Failed, 6 = Queued
    message_type: int

    @property
    def from_me(self) -> bool:
        return self.message_type == 2


def messages() -> Iterator[Res[Message]]:
    files = get_files(config.export_path, glob='sms-*.xml')

    emitted: set[tuple[datetime, str | None, bool]] = set()
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
    tr = _parse_xml(path)
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


class MMSContentPart(NamedTuple):
    sequence_index: int
    content_type: str
    filename: str
    text: str | None
    data: str | None


class MMS(NamedTuple):
    dt: datetime
    dt_readable: str
    parts: list[MMSContentPart]
    # NOTE: these is often something like 'Name 1, Name 2', but might be different depending on your client
    who: str | None
    # NOTE: This can be a single phone number, or multiple, split by '~' or ','. Its better to think
    # of this as a 'key' or 'conversation ID', phone numbers are also present in 'addresses'
    phone_number: str
    addresses: list[tuple[str, int]]
    # 1 = Received, 2 = Sent, 3 = Draft, 4 = Outbox
    message_type: int

    @property
    def from_user(self) -> str:
        # since these can be group messages, we can't just check message_type,
        # we need to iterate through and find who sent it
        # who is CC/'To' is not obvious in many message clients
        #
        # 129 = BCC, 130 = CC, 151 = To, 137 = From
        for (addr, _type) in self.addresses:
            if _type == 137:
                return addr
        # hmm, maybe return instead? but this probably shouldn't happen, means
        # something is very broken
        raise RuntimeError(f'No from address matching 137 found in {self.addresses}')

    @property
    def from_me(self) -> bool:
        return self.message_type == 2


def mms() -> Iterator[Res[MMS]]:
    files = get_files(config.export_path, glob='sms-*.xml')

    emitted: set[tuple[datetime, str | None, str]] = set()
    for p in files:
        for c in _extract_mms(p):
            if isinstance(c, Exception):
                yield c
                continue
            key = (c.dt, c.phone_number, c.from_user)
            if key in emitted:
                continue
            emitted.add(key)
            yield c


def _resolve_null_str(value: str | None) -> str | None:
    if value is None:
        return None
    # hmm.. there's some risk of the text actually being 'null', but there's
    # no way to distinguish that from XML values
    if value == 'null':
        return None
    return value


def _extract_mms(path: Path) -> Iterator[Res[MMS]]:
    tr = _parse_xml(path)
    for mxml in tr.findall('mms'):
        dt = mxml.get('date')
        dt_readable = mxml.get('readable_date')
        message_type = mxml.get('msg_box')

        who = mxml.get('contact_name')
        if who is not None and who in UNKNOWN:
            who = None
        phone_number = mxml.get('address')

        if dt is None or dt_readable is None or message_type is None or phone_number is None:
            mxml_str = etree.tostring(mxml).decode('utf-8')
            yield RuntimeError(f'Missing one or more required attributes [date, readable_date, msg_box, address] in {mxml_str}')
            continue

        addresses: list[tuple[str, int]] = []
        for addr_parent in mxml.findall('addrs'):
            for addr in addr_parent.findall('addr'):
                addr_data = addr.attrib
                user_address = addr_data.get('address')
                user_type = addr_data.get('type')
                if user_address is None or user_type is None:
                    addr_str = etree.tostring(addr_parent).decode()
                    yield RuntimeError(f'Missing one or more required attributes [address, type] in {addr_str}')
                    continue
                if not user_type.isdigit():
                    yield RuntimeError(f'Invalid address type {user_type} {type(user_type)}, cannot convert to number')
                    continue
                addresses.append((user_address, int(user_type)))

        content: list[MMSContentPart] = []

        for part_root in mxml.findall('parts'):

            for part in part_root.findall('part'):

                # the first item is an SMIL XML element encoded as a string which describes
                # how the rest of the parts are laid out
                # https://www.w3.org/TR/SMIL3/smil-timing.html#Timing-TimeContainerSyntax
                # An example:
                # <smil><head><layout><root-layout/><region id="Text" top="0" left="0" height="100%" width="100%"/></layout></head><body><par dur="5000ms"><text src="text.000000.txt" region="Text" /></par></body></smil>
                #
                # This seems pretty useless, so we should try and skip it, and just return the
                # text/images/data
                part_data: dict[str, Any] = part.attrib
                seq: str | None = part_data.get('seq')
                if seq == '-1':
                    continue

                if seq is None or not seq.isdigit():
                    yield RuntimeError(f'seq must be a number, was seq={seq} {type(seq)} in {part_data}')
                    continue

                charset_type: str | None = _resolve_null_str(part_data.get('ct'))
                filename: str | None = _resolve_null_str(part_data.get('name'))
                # in some cases (images, cards), the filename is set in 'cl' instead
                if filename is None:
                    filename = _resolve_null_str(part_data.get('cl'))
                text: str | None = _resolve_null_str(part_data.get('text'))
                data: str | None = _resolve_null_str(part_data.get('data'))

                if charset_type is None or filename is None or (text is None and data is None):
                    yield RuntimeError(f'Missing one or more required attributes [ct, name, (text, data)] must be present in {part_data}')
                    continue

                content.append(
                    MMSContentPart(
                        sequence_index=int(seq),
                        content_type=charset_type,
                        filename=filename,
                        text=text,
                        data=data
                    )
                )

        yield MMS(
            dt=_parse_dt_ms(dt),
            dt_readable=dt_readable,
            who=who,
            phone_number=phone_number,
            message_type=int(message_type),
            parts=content,
            addresses=addresses,
        )


# See https://github.com/karlicoss/HPI/pull/90#issuecomment-702422351
# for potentially parsing timezone from the readable_date
def _parse_dt_ms(d: str) -> datetime:
    return datetime.fromtimestamp(int(d) / 1000, tz=timezone.utc)


def stats() -> Stats:
    return {
        **stat(calls),
        **stat(messages),
        **stat(mms),
    }
