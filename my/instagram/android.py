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


# todo not sure about order of fields...
@dataclass
class _BaseMessage:
    id: str
    created: datetime
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


from ..core import Json
def _parse_message(j: Json) -> Optional[_Message]:
    id = j['item_id']
    t = j['item_type']
    tid = j['thread_key']['thread_id']
    uid = j['user_id']
    # TODO not sure if utc??
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
        raise RuntimeError(f"{id}: {t} isn't handled yet")

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
from ..core.error import Res
import sqlite3
from ..core.sqlite import sqlite_connect_immutable
def _entities() -> Iterator[Res[Union[User, _Message]]]:
    # NOTE: definitely need to merge multiple, app seems to recycle old messages
    # TODO: hmm hard to guarantee timestamp ordering when we use synthetic input data...
    for f in inputs():
        with sqlite_connect_immutable(f) as db:

            for row in db.execute(f'SELECT user_id, thread_info FROM threads'):
                (self_uid, js,) = row
                # ugh wtf?? no easier way to extract your own user id/name??
                yield User(
                    id=str(self_uid),
                    full_name='You',
                    username='you',
                )
                j = json.loads(js)
                for r in j['recipients']:
                    yield User(
                        id=str(r['id']), # for some reason it's int in the db
                        full_name=r['full_name'],
                        username=r['username'],
                    )

            for row in db.execute(f'SELECT message FROM messages ORDER BY timestamp'):
                # eh, seems to contain everything in json?
                (js,) = row
                j = json.loads(js)
                try:
                    m = _parse_message(j)
                    if m is not None:
                        yield m
                except Exception as e:
                    yield e


def messages() -> Iterator[Res[Message]]:
    # TODO would be nicer to use a decorator for unique_everseen?
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
        assert False, type(x)  # should not happen
