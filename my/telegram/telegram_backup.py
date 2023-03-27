"""
Telegram data via [fabianonline/telegram_backup](https://github.com/fabianonline/telegram_backup) tool
"""

from dataclasses import dataclass
from datetime import datetime, timezone
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
def _message_from_row(r: sqlite3.Row, *, chats: Chats) -> Message:
    ts = r['time']
    # desktop export uses UTC (checked by exporting in winter time vs summer time)
    # and telegram_backup timestamps seem same as in desktop export
    time = datetime.fromtimestamp(ts, tz=timezone.utc)
    chat = chats[r['source_id']]
    sender = chats[r['sender_id']]
    return Message(
        id=r['message_id'],
        time=time,
        chat=chat,
        sender=User(id=sender.id, name=sender.name),
        text=r['text'],
    )


def messages() -> Iterator[Message]:
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

        for r in db.execute('SELECT * FROM messages WHERE message_type NOT IN ("service_message", "empty_message") ORDER BY time'):
            # seems like the only remaining have message_type = 'message'
            yield _message_from_row(r, chats=chats)

