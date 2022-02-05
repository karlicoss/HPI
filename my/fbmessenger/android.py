"""
Messenger data from Android app database (in =/data/data/com.facebook.orca/databases/threads_db2=)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Sequence, Optional, Dict


from my.config import fbmessenger as user_config


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
class Sender:
    id: str
    name: str


@dataclass(unsafe_hash=True)
class Thread:
    id: str
    name: Optional[str]

# todo not sure about order of fields...
@dataclass
class _BaseMessage:
    id: str
    dt: datetime
    text: Optional[str]


@dataclass(unsafe_hash=True)
class _Message(_BaseMessage):
    thread_id: str
    sender_id: str
    reply_to_id: Optional[str]


# todo hmm, on the one hand would be kinda nice to inherit common.Message protocol here
# on the other, because the properties there are read only we can't construct the object anymore??
@dataclass(unsafe_hash=True)
class Message(_BaseMessage):
    thread: Thread
    sender: Sender
    reply_to: Optional[Message]


import json
from typing import Union
from ..core.error import Res
from ..core.dataset import connect_readonly
Entity = Union[Sender, Thread, _Message]
def _entities() -> Iterator[Res[Entity]]:
    for f in inputs():
        with connect_readonly(f) as db:
            yield from _process_db(db)


def _process_db(db) -> Iterator[Res[Entity]]:
    # works both for GROUP:group_id and ONE_TO_ONE:other_user:your_user
    threadkey2id = lambda key: key.split(':')[1]

    for r in db['threads']:
        try:
            yield Thread(
                id=threadkey2id(r['thread_key']),
                name=r['name'],
            )
        except Exception as e:
            yield e
            continue

    for r in db['messages'].all(order_by='timestamp_ms'):
        mtype = r['msg_type']
        if mtype == -1:
            # likely immediately deleted or something? doesn't have any data at all
            continue

        user_id = None
        try:
            # todo could use thread_users?
            sj = json.loads(r['sender'])
            ukey = sj['user_key']
            prefix = 'FACEBOOK:'
            assert ukey.startswith(prefix), ukey
            user_id = ukey[len(prefix):]
            yield Sender(
                id=user_id,
                name=sj['name'],
            )
        except Exception as e:
            yield e
            continue

        thread_id = None
        try:
            thread_id = threadkey2id(r['thread_key'])
        except Exception as e:
            yield e
            continue

        try:
            assert user_id is not None
            assert thread_id is not None
            yield _Message(
                id=r['msg_id'],
                dt=datetime.fromtimestamp(r['timestamp_ms'] / 1000),
                # is_incoming=False, TODO??
                text=r['text'],
                thread_id=thread_id,
                sender_id=user_id,
                reply_to_id=r['message_replied_to_id']
            )
        except Exception as e:
            yield e


from more_itertools import unique_everseen
def messages() -> Iterator[Res[Message]]:
    senders: Dict[str, Sender] = {}
    msgs: Dict[str, Message] = {}
    threads: Dict[str, Thread] = {}
    for x in unique_everseen(_entities()):
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, Sender):
            senders[x.id] = x
            continue
        if isinstance(x, Thread):
            threads[x.id] = x
            continue
        if isinstance(x, _Message):
            reply_to_id = x.reply_to_id
            try:
                sender = senders[x.sender_id]
                # hmm, reply_to be missing due to the synthetic nature of export
                # also would be interesting to merge together entities rather than resuling messages from different sources..
                # then the merging thing could be moved to common?
                reply_to = None if reply_to_id is None else msgs[reply_to_id]
                thread = threads[x.thread_id]
            except Exception as e:
                yield e
                continue
            m = Message(
                id=x.id,
                dt=x.dt,
                text=x.text,
                thread=thread,
                sender=sender,
                reply_to=reply_to,
            )
            msgs[m.id] = m
            yield m
            continue
        assert False, type(x)  # should be unreachable
