"""
Bumble data from Android app database (in =/data/data/com.instagram.android/databases/direct.db=)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Sequence, Optional, Dict

from more_itertools import unique_everseen

from my.config import instagram as user_config


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
class User:
    id: str
    username: str
    full_name: str


from ..core import datetime_naive
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
    # TODO could also extract Thread objec? not sure if useful
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

    def __hash__(self, other):
        return hash(self.rest)

    def __eq__(self, other) -> bool:
        if not isinstance(other, MessageError):
            return False
        return self.rest == other.rest


from ..core import Json
def _parse_message(j: Json) -> Optional[_Message]:
    id = j['item_id']
    t = j['item_type']
    tid = j['thread_key']['thread_id']
    uid = j['user_id']
    created = datetime.fromtimestamp(int(j['timestamp']) / 1_000_000)
    text: str
    if t == 'text':
        text = j['text']
    elif t == 'reel_share':
        # TODO include reel_share -> media??
        # the problem is that the links are deliberately expired by instagram..
        text = j['reel_share']['text']
    elif t == 'action_log':
        # something like "X liked message" -- hardly useful?
        return None
    else:
        raise MessageError(id, f"{t} isn't handled yet")

    return _Message(
        id=id,
        created=created,
        text=text,
        thread_id=tid,
        user_id=uid,
        # reply_to_id='FIXME',
    )


import json
from typing import Union
from ..core import Res, assert_never
import sqlite3
from ..core.sqlite import sqlite_connect_immutable, select
def _entities() -> Iterator[Res[Union[User, _Message]]]:
    # NOTE: definitely need to merge multiple, app seems to recycle old messages
    # TODO: hmm hard to guarantee timestamp ordering when we use synthetic input data...
    # todo use TypedDict?
    for f in inputs():
        with sqlite_connect_immutable(f) as db:

            for (self_uid, thread_json) in select(('user_id', 'thread_info'), 'FROM threads', db=db):
                j = json.loads(thread_json)
                # todo in principle should leave the thread attached to the message?
                # since thread is a group of users?
                # inviter usually contains our own user
                for r in [j['inviter'], *j['recipients']]:
                    yield User(
                        id=str(r['id']), # for some reason it's int in the db
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


def messages() -> Iterator[Res[Message]]:
    id2user: Dict[str, User] = {}
    for x in unique_everseen(_entities()):
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
