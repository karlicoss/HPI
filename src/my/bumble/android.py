"""
Bumble data from Android app database (in =/data/data/com.bumble.app/databases/ChatComDatabase=)
"""

from __future__ import annotations

import base64
import json
import sqlite3
from abc import abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, assert_never

from more_itertools import unique_everseen

from my.core import Paths, Res, get_files
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
        Seems like there is no information about our own name in the database.
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
    is_self: bool = False


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
    sender_id: str
    reply_to_id: str | None


@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    chat: Person
    sender: Person
    reply_to: Message | None


EntitiesRes = Res[Person | _Message]


def _entities() -> Iterator[EntitiesRes]:
    config = make_config()

    for db_file in inputs():
        with sqlite_connection(db_file, immutable=True) as db:
            yield from _handle_db(db, my_name=config.my_name)


def _decode_encrypted_user_id(encrypted_user_id: str) -> str:
    # All observed sender_id, recipient_id, and encrypted_user_id values use z followed by unpadded URL-safe Base64.
    # The decoded envelope contains a plaintext target user id, optional account context,
    #   and an apparent 32-byte authenticator.
    assert encrypted_user_id.startswith('z'), encrypted_user_id

    payload = encrypted_user_id[1:]
    padding = '=' * (-len(payload) % 4)
    decoded = base64.b64decode(payload + padding, altchars=b'-_', validate=True)

    assert decoded[:2] == b'\x02\x13', decoded
    user_id_size = int.from_bytes(decoded[2:4], byteorder='big')
    user_id_end = 4 + user_id_size
    user_id = decoded[4:user_id_end].decode()
    assert user_id.isdecimal(), user_id

    context_size = decoded[user_id_end]
    authenticator_size_offset = user_id_end + 1 + context_size
    authenticator_size = decoded[authenticator_size_offset]
    assert authenticator_size == 32, decoded
    assert len(decoded[authenticator_size_offset + 1 :]) == authenticator_size, decoded

    return user_id


def test_decode_encrypted_user_id() -> None:
    # fabricated string just for test, not real data
    encrypted_user_id = 'zAhMACjEyMzQ1Njc4OTAIsWjeOgAAAAAgAAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8'
    assert _decode_encrypted_user_id(encrypted_user_id) == '1234567890'


def _extract_message_text(*, payload_type: str, payload: str) -> str:
    data = json.loads(payload)

    if payload_type == 'QUESTION_GAME':
        return '\n'.join(
            (
                f"Question: {data['text']}",
                f"My answer: {data['answer_own']}",
                f"Their answer: {data['answer_other']}",
            )
        )
    if payload_type == 'VIDEO_CALL':
        return f"Video call duration: {data['duration']} seconds"

    key = {
        'TEXT' : 'text',
        'IMAGE': 'url',
        'GIF'  : 'url',
        'AUDIO': 'url',
        'VIDEO': 'url',
    }[payload_type]  # fmt: skip
    return data[key]


def test_extract_message_text() -> None:
    question_game = json.dumps(
        {
            'text': 'Tea or coffee?',
            'answer_own': 'Tea',
            'answer_other': 'Coffee',
        }
    )
    assert _extract_message_text(payload_type='QUESTION_GAME', payload=question_game) == (
        'Question: Tea or coffee?\nMy answer: Tea\nTheir answer: Coffee'
    )

    video_call = json.dumps({'duration': 42})
    assert _extract_message_text(payload_type='VIDEO_CALL', payload=video_call) == 'Video call duration: 42 seconds'


def _handle_db(db: sqlite3.Connection, *, my_name: str) -> Iterator[EntitiesRes]:
    # For a one-to-one conversation, let M (for Myself) be the current account's numeric id and P be the peer's:
    # - conversation_info.user_id == message.conversation_id == P
    # - incoming: decode(sender_id) == P; decode(recipient_id) == M
    # - outgoing: decode(sender_id) == M; decode(recipient_id) == P
    # Therefore incoming recipient_id and outgoing sender_id both identify M.
    # A non-empty database has one self id, while separate account incarnations can have different ids.
    self_user_ids = {
        _decode_encrypted_user_id(encrypted_user_id)
        for (encrypted_user_id,) in select(
            ('recipient_id',),
            'FROM message WHERE is_incoming = 1 UNION SELECT sender_id FROM message WHERE is_incoming = 0',
            db=db,
        )
    }
    assert len(self_user_ids) <= 1, self_user_ids
    if len(self_user_ids) == 1:
        [self_user_id] = self_user_ids
        yield Person(
            user_id=self_user_id,
            user_name=my_name,
            is_self=True,
        )

    # todo hmm not sure
    # on the one hand kinda nice to use dataset..
    # on the other, it's somewhat of a complication, and
    # would be nice to have something type-directed for sql queries though
    # e.g. with typeddict or something, so the number of parameter to the sql query matches?
    # conversation_info contains peer P but no row for current account M.
    for   user_id ,  user_name in select(
        ('user_id', 'user_name'),
        'FROM conversation_info',
        db=db,
    ):  # fmt: skip
        yield Person(
            user_id=user_id,
            user_name=user_name,
        )

    # NOTE
    # 'message' table:
    # - sender_name and sender_avatar_url are only populated together on a few incoming messages.
    # - Later snapshots of the same messages clear both fields, presumably during synchronization.
    for  mid ,  conversation_id ,  sender_id ,  created           ,  is_incoming ,  payload_type ,  payload ,  reply_to_id in select(
        ('id', 'conversation_id', 'sender_id', 'created_timestamp', 'is_incoming', 'payload_type', 'payload', 'reply_to_id'),
        'FROM message ORDER BY created_timestamp',
        db=db,
    ):  # fmt: skip
        try:
            text = _extract_message_text(payload_type=payload_type, payload=payload)
            yield _Message(
                id=mid,
                # TODO not sure if utc??
                created=datetime.fromtimestamp(created / 1000),
                is_incoming=bool(is_incoming),
                text=text,
                conversation_id=conversation_id,
                sender_id=_decode_encrypted_user_id(sender_id),
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
    # TODO QUESTION_GAME payloads can gain answer_other in later database snapshots.
    # This currently emits multiple messages with the same id; prefer the latest, most complete version.
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

            sender = person if x.is_incoming else id2person[x.sender_id]

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


# Reference for Bumble's Android private storage and ChatComDatabase schema:
# Barros et al., "Forensic Analysis of the Bumble Dating App for Android" https://www.mdpi.com/2673-6756/2/1/16/pdf
