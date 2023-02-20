"""
Telegram data via [fabianonline/telegram_backup](https://github.com/fabianonline/telegram_backup) tool
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Dict, Iterator

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
    name: str
    # not sure if need type?


@dataclass
class User:
    id: str
    name: str


@dataclass
class Message:
    id: int
    time: datetime_aware
    chat: Chat
    sender: User
    text: str


Chats = Dict[str, Chat]
def _message_from_row(r: sqlite3.Row, *, chats: Chats) -> Message:
    ts = r['time']
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
        for r in db.execute('SELECT * FROM chats'):
            chat = Chat(id=r['id'], name=r['name'])
            assert chat.id not in chats
            chats[chat.id] = chat

        for r in db.execute('SELECT * FROM users'):
            chat = Chat(id=r['id'], name=f'{r["first_name"]} {r["last_name"]}')
            assert chat.id not in chats
            chats[chat.id] = chat

        # TODO order by? not sure
        for r in db.execute('SELECT * FROM messages WHERE message_type NOT IN ("service_message", "empty_message")'):
            # seems like the only remaining have message_type = 'message'
            yield _message_from_row(r, chats=chats)

