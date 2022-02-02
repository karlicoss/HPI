"""
Bumble data from Android app database (in =/data/data/com.bumble.app/databases/ChatComDatabase=)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Sequence, Optional, Dict


from my.config import bumble as user_config


from ..core import Paths
@dataclass
class config(user_config.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths


from ..core import get_files
from pathlib import Path
def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


@dataclass(unsafe_hash=True)
class Person:
    user_id: str
    user_name: str


# todo not sure about order of fields...
@dataclass
class _BaseMessage:
    id: str
    created: datetime
    is_incoming: bool
    text: str


@dataclass(unsafe_hash=True)
class _Message(_BaseMessage):
    conversation_id: str
    reply_to_id: Optional[str]


@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    person: Person
    reply_to: Optional[Message]


import json
from typing import Union
from ..core.error import Res
import sqlite3
from ..core.sqlite import sqlite_connect_immutable
def _entities() -> Iterator[Res[Union[Person, _Message]]]:
    last = max(inputs()) # TODO -- need to merge multiple?
    with sqlite_connect_immutable(last) as db:
        for row in db.execute(f'SELECT user_id, user_name FROM conversation_info'):
            (user_id, user_name) = row
            yield Person(
                user_id=user_id,
                user_name=user_name,
            )

        # has sender_name, but it's always None
        for row in db.execute(f'''
        SELECT id, conversation_id, created_timestamp, is_incoming, payload_type, payload, reply_to_id
        FROM message
        ORDER BY created_timestamp
        '''):
            (id, conversation_id, created, is_incoming, payload_type, payload, reply_to_id) = row
            try:
                key = {'TEXT': 'text', 'QUESTION_GAME': 'text', 'IMAGE': 'url', 'GIF': 'url'}[payload_type]
                text = json.loads(payload)[key]
                yield _Message(
                    id=id,
                    # TODO not sure if utc??
                    created=datetime.fromtimestamp(created / 1000),
                    is_incoming=bool(is_incoming),
                    text=text,
                    conversation_id=conversation_id,
                    reply_to_id=reply_to_id,
                )
            except Exception as e:
                yield e


def messages() -> Iterator[Res[Message]]:
    id2person: Dict[str, Person] = {}
    id2msg: Dict[str, Message] = {}
    for x in _entities():
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, Person):
            id2person[x.user_id] = x
            continue
        if isinstance(x, _Message):
            reply_to_id = x.reply_to_id
            try:
                person = id2person[x.conversation_id]
                reply_to = None if reply_to_id is None else id2msg[reply_to_id]
            except Exception as e:
                yield e
                continue
            m = Message(
                id=x.id,
                created=x.created,
                is_incoming=x.is_incoming,
                text=x.text,
                person=person,
                reply_to=reply_to,
            )
            id2msg[m.id] = m
            yield m
            continue
        assert False, type(x)  # should be unreachable
