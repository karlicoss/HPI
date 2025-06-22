"""
Bumble data from Android app database (in =/data/data/com.bumble.app/databases/ChatComDatabase=)
"""

from __future__ import annotations

import json
import sqlite3
from abc import abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, Union

from more_itertools import unique_everseen

from my.core import Paths, Res, get_files
from my.core.compat import assert_never
from my.core.sqlite import select, sqlite_connection


class Config(Protocol):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """
        Paths[s]/glob to the exported sqlite databases
        """
        raise NotImplementedError

    @property
    def my_name(self) -> str:
        """
        Seems like there is no information about our own user in the database (not even name!).
        So if you want, you can supply the module with your name here.
        """
        return "me"


def make_config() -> Config:
    from my.config import bumble as user_config

    class combined_config(user_config.android, Config): ...

    return combined_config()


def inputs() -> Sequence[Path]:
    # TODO not ideal that we instantiate config here and in _entities...
    # perhaps should extract in a class (e.g. Processor or something like that)
    config = make_config()
    return get_files(config.export_path)


@dataclass(unsafe_hash=True)
class Person:
    user_id: str
    user_name: str


_MYSELF_USER_ID = '000000000'


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
    chat: Person
    sender: Person
    reply_to: Message | None


EntitiesRes = Res[Union[Person, _Message]]


def _entities() -> Iterator[EntitiesRes]:
    # Seems like there is no information about our own user in the database (not even name!), and there is no stable id we can rely on.
    # So we just make up a syncthetic user, and let the user specify the name in config
    config = make_config()

    yield Person(
        user_id=_MYSELF_USER_ID,
        user_name=config.my_name,
    )

    for db_file in inputs():
        with sqlite_connection(db_file, immutable=True) as db:
            yield from _handle_db(db)


def _handle_db(db: sqlite3.Connection) -> Iterator[EntitiesRes]:
    # todo hmm not sure
    # on the one hand kinda nice to use dataset..
    # on the other, it's somewhat of a complication, and
    # would be nice to have something type-directed for sql queries though
    # e.g. with typeddict or something, so the number of parameter to the sql query matches?
    # fmt: off
    for   user_id ,  user_name in select(
        ('user_id', 'user_name'),
        'FROM conversation_info',
        db=db,
    ):
    # fmt: on
        yield Person(
            user_id=user_id,
            user_name=user_name,
        )

    # NOTE
    # 'message' table:
    # - has sender_name, but it's always None
    # - has sender_id and recipient_id, but seems like they might change between app reinstalls?
    # - whereas conversation_id is surprisingly stable, e.g. even between account deletions/restores
    #     (checked on "Bumble" user)
    # fmt: off
    for  mid ,  conversation_id ,  created           ,  is_incoming ,  payload_type ,  payload ,  reply_to_id in select(
        ('id', 'conversation_id', 'created_timestamp', 'is_incoming', 'payload_type', 'payload', 'reply_to_id'),
        'FROM message ORDER BY created_timestamp',
        db=db,
    ):
    # fmt: on
        try:
            key = {'TEXT': 'text', 'QUESTION_GAME': 'text', 'IMAGE': 'url', 'GIF': 'url', 'AUDIO': 'url', 'VIDEO': 'url'}[payload_type]
            text = json.loads(payload)[key]
            yield _Message(
                id=mid,
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

            reply_to: Message | None = None
            if reply_to_id is not None:
                try:
                    reply_to = id2msg[reply_to_id]
                except Exception as e:
                    # defensive here, not a huge deal if we lost reply_to
                    yield e

            sender = person if x.is_incoming else id2person[_MYSELF_USER_ID]

            m = Message(
                id=x.id,
                created=x.created,
                # todo hmm is_incoming is a bit redundant?
                # think whether it can be useful in other providers or done in some generic way
                is_incoming=x.is_incoming,
                text=x.text,
                chat=person,
                sender=sender,
                reply_to=reply_to,
            )
            id2msg[m.id] = m
            yield m
            continue
        assert_never(x)
