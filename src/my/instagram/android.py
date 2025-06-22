"""
Bumble data from Android app database (in =/data/data/com.instagram.android/databases/direct.db=)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from my.core import (
    Json,
    Paths,
    Res,
    datetime_naive,
    get_files,
    make_config,
    make_logger,
)
from my.core.cachew import mcachew
from my.core.common import unique_everseen
from my.core.compat import add_note, assert_never
from my.core.json import json_loads
from my.core.sqlite import select, sqlite_connect_immutable

from my.config import instagram as user_config  # isort: skip

logger = make_logger(__name__)


@dataclass
class instagram_android_config(user_config.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths

    # sadly doesn't seem easy to extract user's own handle/name from the db...
    # todo maybe makes more sense to keep in parent class? not sure...
    username: str | None = None
    full_name: str | None = None


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


# this is kinda experimental
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


def _parse_message(j: Json, tid_map: dict[str, str]) -> _Message | None:
    id = j['item_id']  # noqa: A001
    t = j['item_type']

    local_tid = j['thread_key']['thread_id']

    # NOTE: j['thread_key']['thread_v2_id'] also contains server thread id in most cases
    # however sometimes it's missing (perhaps if we are offline?)
    # it seems that using the thread_v2_id from 'threads' table resutls is more reliable

    # NOTE: this is the same id as in gdpr export
    # ... well kind of. For latest android databases it seems to match
    # But seems like it actually changes throughout time (perhaps in 2023/2024 there was some sort of migration for all users??)
    # Overall doesn't seem like there is no obvious logic for it... so we still can't realy on thread id for merging..
    thread_v2_id = tid_map.get(local_tid)
    if thread_v2_id is None:
        # it still is missing somehow (perhaps if we messaged a user while offline/no network?)
        # in general it's not an issue, we'll get the same message from a later export
        # todo not sure if we should emit exception or something instead..
        return None

    uid = j['user_id']
    created: datetime_naive = datetime.fromtimestamp(int(j['timestamp']) / 1_000_000)
    text: str | None = None
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
        thread_id=thread_v2_id,
        user_id=uid,
        # reply_to_id='FIXME',
    )


def _process_db(db: sqlite3.Connection) -> Iterator[Res[User | _Message]]:
    # TODO ugh. seems like no way to extract username?
    # sometimes messages (e.g. media_share) contain it in message field
    # but generally it's not present. ugh
    for (self_uid,) in select(('user_id',), 'FROM session', db=db):
        yield User(
            id=str(self_uid),
            full_name=config.full_name or 'USERS_OWN_FULL_NAME',
            username=config.full_name or 'USERS_OWN_USERNAME',
        )

    # maps local tid to "server tid" (thread_v2_id)
    tid_map: dict[str, str] = {}

    for (thread_json,) in select(('thread_info',), 'FROM threads', db=db):
        j = json_loads(thread_json)
        thread_v2_id = j.get('thread_v2_id')
        if thread_v2_id is not None:
            # sometimes not present...
            tid_map[j['thread_id']] = thread_v2_id
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
        j = json_loads(msg_json)
        try:
            m = _parse_message(j, tid_map=tid_map)
            if m is not None:
                yield m
        except Exception as e:
            add_note(e, f'^ while parsing {j}')
            yield e


def _entities() -> Iterator[Res[User | _Message]]:
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
                for m in _process_db(db=db):
                    if isinstance(m, Exception):
                        add_note(m, f'^ while processing {path}')
                    yield m
            except Exception as e:
                add_note(e, f'^ while processing {path}')
                yield e
                # todo use error policy here


@mcachew(depends_on=inputs)
def messages() -> Iterator[Res[Message]]:
    id2user: dict[str, User] = {}
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
