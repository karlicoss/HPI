"""
Whatsapp data from Android app database (in =/data/data/com.whatsapp/databases/msgstore.db=)
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from my.core import Paths, Res, datetime_aware, get_files, make_config, make_logger
from my.core.common import unique_everseen
from my.core.error import notnone
from my.core.sqlite import SqliteTool, sqlite_connection

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


Entity = Chat | Sender | Message


# WhatsApp uses key ID -1 for a migration placeholder rather than a real message.
_FAKE_MESSAGE_ID = -1

# WhatsApp uses sender JID row ID 0 when no sender row is available.
_NO_SENDER_JID_ROW_ID = 0

# WhatsApp uses message type 7 for system events such as chat creation or name changes.
_SYSTEM_MESSAGE_TYPE = 7


def _process_db(db: sqlite3.Connection) -> Iterator[Entity]:
    # TODO later, split out Chat/Sender objects separately to safe on object creation, similar to other android data sources

    sqlite = SqliteTool(db)

    # The September 2022 schema migrated rows from `messages` to `message`.
    version_202209 = 'messages' not in sqlite.get_table_names()

    # The September 2024 schema replaced chat JIDs with references to the `jid` table.
    version_202409 = 'jid_row_id' in sqlite.get_table_schema('chat_view')

    if version_202409:
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
        chat_obj = Chat(
            id=chat_id,
            name=subject,
        )
        yield chat_obj
        chats[chat_obj.id] = chat_obj

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

    if version_202209:
        message_table = 'message'
        message_chat_id = chat_id_col
        message_sender_row_id = 'M.sender_jid_row_id'
        message_sender_id = 'NULL'
        message_from_me = 'M.from_me'
        message_text = 'M.text_data'
        message_type = 'M.message_type'
        message_join = f'''
    LEFT JOIN chat_view ON M.chat_row_id = chat_view._id
    {jid_join}
    '''
    else:
        message_table = 'messages'
        message_chat_id = 'M.key_remote_jid'
        message_sender_row_id = str(_NO_SENDER_JID_ROW_ID)
        message_sender_id = 'CASE WHEN M.key_from_me = 1 THEN NULL ELSE M.remote_resource END'
        message_from_me = 'M.key_from_me'
        message_text = 'M.data'
        message_type = 'CAST(M.media_wa_type AS INTEGER)'
        message_join = ''

    # NOTE: message_view and available_message_view expose columns containing mostly NULL values.
    # Querying the underlying message table preserves fields such as attachment paths.
    message_query = f'''
    SELECT
        {message_chat_id} AS chat_id,
        M.key_id, M.timestamp,
        {message_sender_row_id} AS sender_jid_row_id,
        {message_sender_id} AS sender_id,
        {message_from_me} AS from_me,
        {message_text} AS text_data,
        MM.file_path,
        MM.file_size,
        {message_type} AS message_type
    FROM {message_table} AS M
    {message_join}
    LEFT JOIN message_media AS MM ON M._id = MM.message_row_id
    WHERE M.key_id != {_FAKE_MESSAGE_ID}
      AND {message_type} != {_SYSTEM_MESSAGE_TYPE}
    ORDER BY M.timestamp
    '''

    for r in db.execute(message_query):
        msg_id: str = notnone(r['key_id'])
        ts: int = notnone(r['timestamp'])
        dt = datetime.fromtimestamp(ts / 1000, tz=UTC)

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
        chat = chats.get(chat_id)
        if chat is None:
            assert not version_202209, chat_id
            chat = Chat(id=chat_id, name=None)
            yield chat
            chats[chat.id] = chat

        sender_id = r['sender_id']
        if sender_id is not None:
            sender = Sender(id=sender_id, name=None)
        else:
            sender_row_id = r['sender_jid_row_id']
            # seems that it's always 0 for 1-1 chats
            # for group chats our own id is still 0, but other ids are properly set
            if sender_row_id == _NO_SENDER_JID_ROW_ID:
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
                e.add_note(f'^ while processing {path}')


def entities() -> Iterator[Res[Entity]]:
    return unique_everseen(_entities)


def messages() -> Iterator[Res[Message]]:
    # TODO hmm, specify key=lambda m: m.id?
    # not sure since might be useful to keep track of sender changes etc
    # probably best not to, or maybe query messages/senders separately and merge later?
    for e in entities():
        if isinstance(e, (Exception, Message)):
            yield e
