"""
Bumble data from Android app database (in =/data/data/com.bumble.app/databases/ChatComDatabase=)
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from more_itertools import unique_everseen

from my.core import Paths, get_files

from my.config import bumble as user_config  # isort: skip


@dataclass
class config(user_config.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths


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
    reply_to_id: str | None


@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    person: Person
    reply_to: Message | None


import json
import sqlite3
from typing import Union

from my.core.compat import assert_never

from ..core import Res
from ..core.sqlite import select, sqlite_connect_immutable

EntitiesRes = Res[Union[Person, _Message]]

def _entities() -> Iterator[EntitiesRes]:
    for db_file in inputs():
        with sqlite_connect_immutable(db_file) as db:
            yield from _handle_db(db)


def _handle_db(db: sqlite3.Connection) -> Iterator[EntitiesRes]:
    # todo hmm not sure
    # on the one hand kinda nice to use dataset..
    # on the other, it's somewhat of a complication, and
    # would be nice to have something type-directed for sql queries though
    # e.g. with typeddict or something, so the number of parameter to the sql query matches?
    for     (user_id,   user_name) in select(
            ('user_id', 'user_name'),
            'FROM conversation_info',
            db=db,
    ):
        yield Person(
            user_id=user_id,
            user_name=user_name,
        )

    # note: has sender_name, but it's always None
    for     ( id,   conversation_id ,  created           ,  is_incoming ,  payload_type ,  payload ,  reply_to_id) in select(
            ('id', 'conversation_id', 'created_timestamp', 'is_incoming', 'payload_type', 'payload', 'reply_to_id'),
            'FROM message ORDER BY created_timestamp',
            db=db
    ):
        try:
            key = {'TEXT': 'text', 'QUESTION_GAME': 'text', 'IMAGE': 'url', 'GIF': 'url', 'AUDIO': 'url', 'VIDEO': 'url'}[payload_type]
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


def _key(r: EntitiesRes):
    if isinstance(r, _Message):
        if '/hidden?' in r.text:
            # ugh. seems that image URLs change all the time in the db?
            # can't access them without login anyway
            # so use a different key for such messages
            # todo maybe normalize text instead? since it's gonna always trigger diffs down the line
            return (r.id, r.created)
    return r


_UNKNOWN_PERSON = "UNKNOWN_PERSON"


def messages() -> Iterator[Res[Message]]:
    id2person: dict[str, Person] = {}
    id2msg: dict[str, Message] = {}
    for x in unique_everseen(_entities(), key=_key):
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, Person):
            id2person[x.user_id] = x
            continue
        if isinstance(x, _Message):
            reply_to_id = x.reply_to_id
            # hmm seems that sometimes there are messages with no corresponding conversation_info?
            # possibly if user never clicked on conversation before..
            person = id2person.get(x.conversation_id)
            if person is None:
                person = Person(user_id=x.conversation_id, user_name=_UNKNOWN_PERSON)
            try:
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
        assert_never(x)
