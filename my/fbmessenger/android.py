"""
Messenger data from Android app database (in =/data/data/com.facebook.orca/databases/threads_db2=)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence, Optional, Dict, Union, List

from my.core import get_files, Paths, datetime_aware, Res, assert_never, LazyLogger, make_config
from my.core.common import unique_everseen
from my.core.error import echain
from my.core.sqlite import sqlite_connection

from my.config import fbmessenger as user_config


logger = LazyLogger(__name__)


@dataclass
class Config(user_config.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths

    facebook_id: Optional[str] = None


# hmm. this is necessary for default value (= None) to work
# otherwise Config.facebook_id is always None..
config = make_config(Config)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


@dataclass(unsafe_hash=True)
class Sender:
    id: str
    name: Optional[str]


@dataclass(unsafe_hash=True)
class Thread:
    id: str
    name: Optional[str]  # isn't set for groups or one to one messages


# todo not sure about order of fields...
@dataclass
class _BaseMessage:
    id: str
    dt: datetime_aware
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


Entity = Union[Sender, Thread, _Message]


def _entities() -> Iterator[Res[Entity]]:
    paths = inputs()
    total = len(paths)
    width = len(str(total))
    for idx, path in enumerate(paths):
        logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
        with sqlite_connection(path, immutable=True, row_factory='row') as db:
            try:
                use_msys = len(list(db.execute('SELECT * FROM sqlite_master WHERE name = "logging_events_v2"'))) > 0
                if use_msys:
                    yield from _process_db_msys(db)
                else:
                    yield from _process_db_threads_db2(db)
            except Exception as e:
                yield echain(RuntimeError(f'While processing {path}'), cause=e)


def _normalise_user_id(ukey: str) -> str:
    # trying to match messages.author from fbchat
    prefix = 'FACEBOOK:'
    assert ukey.startswith(prefix), ukey
    return ukey[len(prefix) :]


def _normalise_thread_id(key) -> str:
    # works both for GROUP:group_id and ONE_TO_ONE:other_user:your_user
    return key.split(':')[1]


# NOTE: this is sort of copy pasted from other _process_db method
# maybe later could unify them
def _process_db_msys(db: sqlite3.Connection) -> Iterator[Res[Entity]]:
    senders: Dict[str, Sender] = {}
    for r in db.execute('SELECT CAST(id AS TEXT) AS id, name FROM contacts'):
        s = Sender(
            id=r['id'],  # looks like it's server id? same used on facebook site
            name=r['name'],
        )
        # NOTE https://www.messenger.com/t/{contant_id} for permalink
        senders[s.id] = s
        yield s

    # TODO what is fb transport??
    # TODO what are client_contacts?? has pk or something

    # TODO client_threads/client_messages -- possibly for end to end encryption or something?

    # TODO can we get it from db? could infer as the most common id perhaps?
    self_id = config.facebook_id
    thread_users: Dict[str, List[Sender]] = {}
    for r in db.execute('SELECT CAST(thread_key AS TEXT) AS thread_key, CAST(contact_id AS TEXT) AS contact_id FROM participants'):
        thread_key = r['thread_key']
        user_key = r['contact_id']

        ll = thread_users.get(thread_key)
        if ll is None:
            ll = []
            thread_users[thread_key] = ll

        if self_id is not None and user_key == self_id:
            # exclude yourself, otherwise it's just spammy to show up in all participants
            # TODO not sure about that, maybe change later
            continue

        ll.append(senders[user_key])

    # 15 is a weird thread that doesn't have any participants and messages
    for r in db.execute('SELECT CAST(thread_key AS TEXT) AS thread_key, thread_name FROM threads WHERE thread_type != 15'):
        thread_key = r['thread_key']
        name = r['thread_name']
        if name is None:
            users = thread_users[thread_key]
            name = ', '.join([u.name or u.id for u in users])
        yield Thread(
            id=thread_key,
            name=name,
        )

    # TODO should be quicker to explicitly specify columns rather than SELECT *
    # should probably add it to module development tips?
    for r in db.execute(
        '''
    SELECT
      message_id,
      timestamp_ms,
      text,
      CAST(thread_key AS TEXT) AS thread_key,
      CAST(sender_id AS TEXT) AS sender_id,
      reply_source_id
    FROM messages
    ORDER BY timestamp_ms /* they aren't in order in the database, so need to sort */
        '''
    ):
        yield _Message(
            id=r['message_id'],
            # TODO double check utc
            dt=datetime.fromtimestamp(r['timestamp_ms'] / 1000, tz=timezone.utc),
            # is_incoming=False, TODO??
            text=r['text'],
            thread_id=r['thread_key'],
            sender_id=r['sender_id'],
            reply_to_id=r['reply_source_id'],
        )


def _process_db_threads_db2(db: sqlite3.Connection) -> Iterator[Res[Entity]]:
    senders: Dict[str, Sender] = {}
    for r in db.execute('''SELECT * FROM thread_users'''):
        # for messaging_actor_type == 'REDUCED_MESSAGING_ACTOR', name is None
        # but they are still referenced, so need to keep
        name = r['name']
        user_key = r['user_key']
        s = Sender(
            id=_normalise_user_id(user_key),
            name=name,
        )
        senders[user_key] = s
        yield s

    self_id = config.facebook_id
    thread_users: Dict[str, List[Sender]] = {}
    for r in db.execute('SELECT * from thread_participants'):
        thread_key = r['thread_key']
        user_key = r['user_key']
        if self_id is not None and user_key == f'FACEBOOK:{self_id}':
            # exclude yourself, otherwise it's just spammy to show up in all participants
            continue

        ll = thread_users.get(thread_key)
        if ll is None:
            ll = []
            thread_users[thread_key] = ll
        ll.append(senders[user_key])

    for r in db.execute('SELECT * FROM threads'):
        thread_key = r['thread_key']
        thread_type = thread_key.split(':')[0]
        if thread_type == 'MONTAGE':  # no idea what this is?
            continue
        name = r['name']  # seems that it's only set for some groups
        if name is None:
            users = thread_users[thread_key]
            name = ', '.join([u.name or u.id for u in users])
        yield Thread(
            id=_normalise_thread_id(thread_key),
            name=name,
        )

    for r in db.execute(
        '''
    SELECT *, json_extract(sender, "$.user_key") AS user_key FROM messages 
    WHERE msg_type NOT IN (
        -1,  /* these don't have any data at all, likely immediately deleted or something? */
        2    /* these are 'left group' system messages, also a bit annoying since they might reference nonexistent users */
    )
    ORDER BY timestamp_ms /* they aren't in order in the database, so need to sort */
        '''
    ):
        yield _Message(
            id=r['msg_id'],
            # double checked against some messages in different timezone
            dt=datetime.fromtimestamp(r['timestamp_ms'] / 1000, tz=timezone.utc),
            # is_incoming=False, TODO??
            text=r['text'],
            thread_id=_normalise_thread_id(r['thread_key']),
            sender_id=_normalise_user_id(r['user_key']),
            reply_to_id=r['message_replied_to_id'],
        )


def contacts() -> Iterator[Res[Sender]]:
    for x in unique_everseen(_entities):
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, Sender):
            yield x


def messages() -> Iterator[Res[Message]]:
    senders: Dict[str, Sender] = {}
    msgs: Dict[str, Message] = {}
    threads: Dict[str, Thread] = {}
    for x in unique_everseen(_entities):
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
            # hmm, reply_to be missing due to the synthetic nature of export, so have to be defensive
            reply_to = None if reply_to_id is None else msgs.get(reply_to_id)
            # also would be interesting to merge together entities rather than resulting messages from different sources..
            # then the merging thing could be moved to common?
            try:
                sender = senders[x.sender_id]
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
        # NOTE: for some reason mypy coverage highlights it as red?
        # but it actually works as expected: i.e. if you omit one of the clauses above, mypy will complain
        assert_never(x)
