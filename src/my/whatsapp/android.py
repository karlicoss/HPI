"""
Whatsapp data from Android app database (in =/data/data/com.whatsapp/databases/msgstore.db=)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

from my.core import Paths, Res, datetime_aware, get_files, make_config, make_logger
from my.core.common import unique_everseen
from my.core.compat import add_note
from my.core.error import notnone
from my.core.sqlite import sqlite_connection

import my.config  # isort: skip

logger = make_logger(__name__)


@dataclass
class Config(my.config.whatsapp.android):
    # paths[s]/glob to the exported sqlite databases
    export_path: Paths
    my_user_id: str | None = None


config = make_config(Config)


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


@dataclass(unsafe_hash=True)
class Chat:
    id: str
    # todo not sure how to support renames?
    # could change Chat object itself, but this won't work well with incremental processing..
    name: str | None


@dataclass(unsafe_hash=True)
class Sender:
    id: str
    name: str | None


@dataclass(unsafe_hash=True)
class Message:
    chat: Chat
    id: str
    dt: datetime_aware
    sender: Sender
    text: str | None


Entity = Union[Chat, Sender, Message]


def _process_db(db: sqlite3.Connection) -> Iterator[Entity]:
    # TODO later, split out Chat/Sender objects separately to safe on object creation, similar to other android data sources

    try:
        db.execute('SELECT jid_row_id FROM chat_view')
    except sqlite3.OperationalError as oe:
        if 'jid_row_id' not in str(oe):
            raise oe
        new_version_202410 = False
    else:
        new_version_202410 = True

    if new_version_202410:
        chat_id_col = 'jid.raw_string'
        jid_join = 'JOIN jid ON jid._id == chat_view.jid_row_id'
    else:
        chat_id_col = 'chat_view.raw_string_jid'
        jid_join = ''

    chats = {}
    for r in db.execute(
        f'''
    SELECT {chat_id_col} AS chat_id, subject
    FROM chat_view {jid_join}
    WHERE chat_id IS NOT NULL /* seems that it might be null for chats that are 'recycled' (the db is more like an LRU cache) */
    '''
    ):
        chat_id = r['chat_id']
        subject = r['subject']
        chat = Chat(
            id=chat_id,
            name=subject,
        )
        yield chat
        chats[chat.id] = chat

    senders = {}
    for r in db.execute(
        '''
    SELECT _id, raw_string
    FROM jid
    '''
    ):
        # TODO seems that msgstore.db doesn't have contact names
        # perhaps should extract from wa.db and match against wa_contacts.jid?
        # TODO these can also be chats? not sure if need to include...
        s = Sender(
            id=r['raw_string'],
            name=None,
        )
        yield s
        senders[r['_id']] = s

    # NOTE: hmm, seems that message_view or available_message_view use lots of NULL as ...
    # so even if it seems as if it has a column (e.g. for attachment path), there is actually no such data
    # so makes more sense to just query message column directly
    for r in db.execute(
        f'''
    SELECT
        {chat_id_col} AS chat_id,
        M.key_id, M.timestamp,
        sender_jid_row_id,
        M.from_me,
        M.text_data,
        MM.file_path,
        MM.file_size,
        M.message_type
    FROM      message       AS M
    LEFT JOIN chat_view     ON M.chat_row_id = chat_view._id
    {jid_join}
    left JOIN message_media AS MM ON M._id = MM.message_row_id
    WHERE M.key_id != -1 /*  key_id -1 is some sort of fake message where everything is null */
           /* type 7 seems to be some dummy system message.
              sometimes contain chat name, but usually null, so ignore them
              for normal messages it's 0
           */
          AND M.message_type != 7
    ORDER BY M.timestamp
    '''
    ):
        msg_id: str = notnone(r['key_id'])
        ts: int = notnone(r['timestamp'])
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

        text: str | None = r['text_data']
        media_file_path: str | None = r['file_path']
        media_file_size: int | None = r['file_size']

        message_type = r['message_type']

        if text is None:
            # fmt: off
            text = {
                5 : '[MAP LOCATION]',
                10: '[MISSED VOICE CALL]',
                15: '[DELETED]',
                16: '[LIVE LOCATION]',
                64: '[DELETED]',  # seems like 'deleted by admin'?
            }.get(message_type)
            # fmt: on

        # check against known msg types
        # fmt: off
        if text is None and message_type not in {
            0,  # normal
            1,  # image
            2,  # voice note
            3,  # video
            7,  # "system" message, e.g. chat name
            8,  # document
            9,  # also document?
            13, # animated gif?
            20, # webp/sticker?
        }:
            text = f"[UNKNOWN TYPE {message_type}]"
        # fmt: on

        if media_file_size is not None:
            # this is always not null for message_media table
            # however media_file_path sometimes may be none
            mm = f'MEDIA: {media_file_path}'
            if text is None:
                text = mm
            else:
                text = text + '\n' + mm

        from_me = r['from_me'] == 1

        chat_id = r['chat_id']
        if chat_id is None:
            # ugh, I think these might have been edited messages? unclear..
            logger.warning(f"CHAT ID IS NONE, WTF?? {dt} {ts} {text}")
            continue
        chat = chats[chat_id]

        sender_row_id = r['sender_jid_row_id']
        if sender_row_id == 0:
            # seems that it's always 0 for 1-1 chats
            # for group chats our own id is still 0, but other ids are properly set
            if from_me:
                myself_user_id = config.my_user_id or 'MYSELF_USER_ID'
                sender = Sender(id=myself_user_id, name=None)  # TODO set my own name as well?
            else:
                sender = Sender(id=chat.id, name=None)
        else:
            sender = senders[sender_row_id]

        m = Message(chat=chat, id=msg_id, dt=dt, sender=sender, text=text)
        yield m


def _entities() -> Iterator[Res[Entity]]:
    paths = inputs()
    total = len(paths)
    width = len(str(total))
    for idx, path in enumerate(paths):
        logger.info(f'processing [{idx:>{width}}/{total:>{width}}] {path}')
        with sqlite_connection(path, immutable=True, row_factory='row') as db:
            try:
                yield from _process_db(db)
            except Exception as e:
                add_note(e, f'^ while processing {path}')


def entities() -> Iterator[Res[Entity]]:
    return unique_everseen(_entities)


def messages() -> Iterator[Res[Message]]:
    # TODO hmm, specify key=lambda m: m.id?
    # not sure since might be useful to keep track of sender changes etc
    # probably best not to, or maybe query messages/senders separately and merge later?
    for e in entities():
        if isinstance(e, (Exception, Message)):
            yield e
