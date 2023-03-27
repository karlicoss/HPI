"""
Telegram data via [fabianonline/telegram_backup](https://github.com/fabianonline/telegram_backup) tool
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from struct import unpack_from, calcsize
import sqlite3
from typing import Dict, Iterator, Optional

from my.core import datetime_aware, PathIsh
from my.core.sqlite import sqlite_connection

from my.config import telegram as user_config


@dataclass
class config(user_config.telegram_backup):
    # path to the export database.sqlite
    export_path: PathIsh
    

@dataclass
class Chat:
    id: str
    name: Optional[str]
    # not all users have short handle + groups don't have them either?
    # TODO hmm some groups have it -- it's just the tool doesn't dump them??
    handle: Optional[str]
    # not sure if need type?


@dataclass
class User:
    id: str
    name: Optional[str]


@dataclass
class Message:
    # NOTE: message id is NOT unique globally -- only with respect to chat!
    id: int
    time: datetime_aware
    chat: Chat
    sender: User
    text: str
    extra_media_info: Optional[str] = None

    @property
    def permalink(self) -> str:
        handle = self.chat.handle
        if handle is None:
            clink = str(self.chat.id)
        else:
            # FIXME add c/
            clink = f'{handle}'

        # NOTE: don't think deep links to messages work for private conversations sadly https://core.telegram.org/api/links#message-links
        # NOTE: doesn't look like this works with private groups at all, doesn't even jump into it
        return f'https://t.me/{clink}/{self.id}'



Chats = Dict[str, Chat]
def _message_from_row(r: sqlite3.Row, *, chats: Chats, with_extra_media_info: bool) -> Message:
    ts = r['time']
    # desktop export uses UTC (checked by exporting in winter time vs summer time)
    # and telegram_backup timestamps seem same as in desktop export
    time = datetime.fromtimestamp(ts, tz=timezone.utc)
    chat = chats[r['source_id']]
    sender = chats[r['sender_id']]

    extra_media_info: Optional[str] = None
    if with_extra_media_info and r['has_media'] == 1:
        # also it's quite hacky, so at least for now it's just an optional attribute behind the flag
        # defensive because it's a bit tricky to correctly parse without a proper api parser..
        # maybe later we'll improve it
        try:
            extra_media_info = _extract_extra_media_info(data=r['data'])
        except Exception as e:
            pass

    return Message(
        id=r['message_id'],
        time=time,
        chat=chat,
        sender=User(id=sender.id, name=sender.name),
        text=r['text'],
        extra_media_info=extra_media_info,
    )


def messages(*, extra_where: Optional[str]=None, with_extra_media_info: bool=False) -> Iterator[Message]:
    messages_query = 'SELECT * FROM messages WHERE message_type NOT IN ("service_message", "empty_message")'
    if extra_where is not None:
        messages_query += ' AND ' + extra_where
    messages_query += ' ORDER BY time'

    with sqlite_connection(config.export_path, immutable=True, row_factory='row') as db:
        chats: Chats = {}
        for r in db.execute('SELECT * FROM chats ORDER BY id'):
            chat = Chat(id=r['id'], name=r['name'], handle=None)
            assert chat.id not in chats
            chats[chat.id] = chat

        for r in db.execute('SELECT * FROM users ORDER BY id'):
            first = r["first_name"]
            last = r["last_name"]
            name: Optional[str]
            if first is not None and last is not None:
                name = f'{first} {last}'
            else:
                name = first or last

            chat = Chat(id=r['id'], name=name, handle=r['username'])
            assert chat.id not in chats
            chats[chat.id] = chat

        for r in db.execute(messages_query):
            # seems like the only remaining have message_type = 'message'
            yield _message_from_row(r, chats=chats, with_extra_media_info=with_extra_media_info)


def _extract_extra_media_info(data: bytes) -> Optional[str]:
    # ugh... very hacky, but it does manage to extract from 90% of messages that have media
    pos = 0

    def skip(count: int) -> None:
        nonlocal pos
        pos += count

    def getstring() -> str:
        # jesus
        # https://core.telegram.org/type/string
        if data[pos] == 254:
            skip(1)
            (sz1, sz2, sz3) = unpack_from('BBB', data, offset=pos)
            skip(3)
            sz = 256 ** 2 * sz3 + 256 * sz2 + sz1
            short = 0
        else:
            (sz, ) = unpack_from('B', data, offset=pos)
            skip(1)
            short = 1
        assert sz > 0, sz

        padding = 0 if (sz + short) % 4 == 0 else 4 - (sz + short) % 4

        (ss,) = unpack_from(f'{sz}s{padding}x', data, offset=pos)
        skip(sz + padding)
        try:
            return ss.decode('utf8')
        except UnicodeDecodeError as e:
            raise RuntimeError(f'Failed to decode {ss}') from e

    def debug(count: int=10) -> None:
        print([hex(x) for x in data[pos: pos + count]])
        print([chr(x) for x in data[pos: pos + count]])

    header = 'H2xII8xI'
    (flags, mid, src, ts) = unpack_from(header, data, offset=pos)
    pos += calcsize(header)

    # see https://core.telegram.org/constructor/message
    has_media = (flags >> 9) & 1
    if has_media == 0:
        return None

    msg_body = getstring()
    skip(20)
    url1 = getstring()
    url2 = getstring()
    ss_type = getstring()
    # not sure if assert is really necessary her
    # assert ss_type in {
    #     'article',
    #     'photo',
    #     'app',
    #     'video',
    # }, ss_type
    link_title = getstring()
    link_title_2 = getstring()
    link_description = getstring()
    return link_description
