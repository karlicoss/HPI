"""
Bumble data from Android app database (in =/data/data/com.instagram.android/databases/direct.db=)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence, Optional, Dict, Union

from my.core import (
    get_files,
    Paths,
    make_config,
    make_logger,
    datetime_naive,
    Json,
    Res,
    assert_never,
)
from my.core.common import unique_everseen
from my.core.cachew import mcachew
from my.core.error import echain
from my.core.sqlite import sqlite_connect_immutable, select

from my.config import instagram as user_config


logger = make_logger(__name__)


@dataclass
class instagram_android_config(user_config.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths

    # sadly doesn't seem easy to extract user's own handle/name from the db...
    # todo maybe makes more sense to keep in parent class? not sure...
    username: Optional[str] = None
    full_name: Optional[str] = None


config = make_config(instagram_android_config)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


@dataclass(unsafe_hash=True)
class User:
    id: str
    username: str
    full_name: str


# todo not sure about order of fields...
@dataclass
class _BaseMessage:
    id: str
    # NOTE: ffs, looks like they keep naive timestamps in the db (checked some random messages)
    created: datetime_naive
    text: str
    thread_id: str


@dataclass(unsafe_hash=True)
class _Message(_BaseMessage):
    user_id: str
    # TODO ugh. can't figure out if dms have proper replies?
    # reply_to_id: Optional[str]


@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    user: User
    # TODO could also extract Thread object? not sure if useful
    # reply_to: Optional[Message]


# this is kinda expecrimental
# basically just using RuntimeError(msg_id, *rest) has an unfortunate consequence:
# there are way too many 'similar' errors (on different msg_id)
# however passing msg_id is nice as a means of supplying extra context
# so this is a compromise, the 'duplicate' errors will be filtered out by unique_everseen


class MessageError(RuntimeError):
    def __init__(self, msg_id: str, *rest: str) -> None:
        super().__init__(msg_id, *rest)
        self.rest = rest

    def __hash__(self):
        return hash(self.rest)

    def __eq__(self, other) -> bool:
        if not isinstance(other, MessageError):
            return False
        return self.rest == other.rest


def _parse_message(j: Json) -> Optional[_Message]:
    id = j['item_id']
    t = j['item_type']
    tid = j['thread_key']['thread_id']
    uid = j['user_id']
    created = datetime.fromtimestamp(int(j['timestamp']) / 1_000_000)
    text: Optional[str] = None
    if t == 'text':
        text = j['text']
    elif t == 'reel_share':
        # TODO include reel_share -> media??
        # the problem is that the links are deliberately expired by instagram..
        text = j['reel_share']['text']
    elif t == 'action_log':
        # for likes this ends up as 'Liked a message' or reactions
        # which isn't super useful by itself perhaps, but matches GDPR so lets us unify threads better
        text = j['action_log']['description']
    else:
        raise MessageError(id, f"{t} isn't handled yet")

    assert text is not None, j

    return _Message(
        id=id,
        created=created,
        text=text,
        thread_id=tid,
        user_id=uid,
        # reply_to_id='FIXME',
    )


def _process_db(db: sqlite3.Connection) -> Iterator[Res[Union[User, _Message]]]:
    # TODO ugh. seems like no way to extract username?
    # sometimes messages (e.g. media_share) contain it in message field
    # but generally it's not present. ugh
    for (self_uid,) in select(('user_id',), 'FROM session', db=db):
        yield User(
            id=str(self_uid),
            full_name=config.full_name or 'USERS_OWN_FULL_NAME',
            username=config.full_name or 'USERS_OWN_USERNAME',
        )

    for (thread_json,) in select(('thread_info',), 'FROM threads', db=db):
        j = json.loads(thread_json)
        # todo in principle should leave the thread attached to the message?
        # since thread is a group of users?
        pre_users = []
        # inviter usually contains our own user
        if 'inviter' in j:
            # sometimes it's missing (e.g. in broadcast channels)
            pre_users.append(j['inviter'])
        pre_users.extend(j['recipients'])
        for r in pre_users:
            # id disappeared and seems that pk_id is in use now (around december 2022)
            uid = r.get('id') or r.get('pk_id')
            assert uid is not None
            yield User(
                id=str(uid),  # for some reason it's int in the db
                full_name=r['full_name'],
                username=r['username'],
            )

    for (msg_json,) in select(('message',), 'FROM messages ORDER BY timestamp', db=db):
        # eh, seems to contain everything in json?
        j = json.loads(msg_json)
        try:
            m = _parse_message(j)
            if m is not None:
                yield m
        except Exception as e:
            yield e


def _entities() -> Iterator[Res[Union[User, _Message]]]:
    # NOTE: definitely need to merge multiple, app seems to recycle old messages
    # TODO: hmm hard to guarantee timestamp ordering when we use synthetic input data...
    # todo use TypedDict?
    paths = inputs()
    total = len(paths)
    width = len(str(total))
    for idx, path in enumerate(paths):
        logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
        with sqlite_connect_immutable(path) as db:
            try:
                yield from _process_db(db=db)
            except Exception as e:
                # todo use error policy here
                yield echain(RuntimeError(f'While processing {path}'), cause=e)


@mcachew(depends_on=inputs)
def messages() -> Iterator[Res[Message]]:
    id2user: Dict[str, User] = {}
    for x in unique_everseen(_entities):
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, User):
            id2user[x.id] = x
            continue
        if isinstance(x, _Message):
            try:
                user = id2user[x.user_id]
            except Exception as e:
                yield e
                continue
            yield Message(
                id=x.id,
                created=x.created,
                text=x.text,
                thread_id=x.thread_id,
                user=user,
            )
            continue
        assert_never(x)
