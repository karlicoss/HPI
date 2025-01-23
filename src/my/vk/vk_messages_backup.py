'''
VK data (exported by [[https://github.com/Totktonada/vk_messages_backup][Totktonada/vk_messages_backup]])
'''
# note: could reuse the original repo, but little point I guess since VK closed their API
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

import pytz

from my.config import vk_messages_backup as config
from my.core import Json, Res, Stats, datetime_aware, get_files, stat
from my.core.common import unique_everseen

# I think vk_messages_backup used this tz?
# not sure if vk actually used to return this tz in api?
TZ = pytz.timezone('Europe/Moscow')


Uid = int


@dataclass(frozen=True)
class User:
    id: Uid
    first_name: str
    last_name: str


@dataclass(frozen=True)
class Chat:
    chat_id: str
    title: str


@dataclass(frozen=True)
class Message:
    dt: datetime_aware
    chat: Chat
    id: str  # todo not sure it's unique?
    user: User
    body: str


Users = dict[Uid, User]


def users() -> Users:
    files = get_files(config.storage_path, glob='user_*.json')
    res = {}
    for f in files:
        j = json.loads(f.read_text())
        uid = j['id']
        res[uid] = User(
            id=uid,
            first_name=j['first_name'],
            last_name=j['last_name'],
        )
    return res


GROUP_CHAT_MIN_ID = 2000000000


def _parse_chat(*, msg: Json, udict: Users) -> Chat:
    # exported with newer api, peer_id is a proper identifier both for users and chats
    peer_id = msg.get('peer_id')
    if peer_id is not None:
        chat_id = peer_id
    else:
        group_chat_id = msg.get('chat_id')
        if group_chat_id is not None:
            chat_id = GROUP_CHAT_MIN_ID + group_chat_id
        else:
            chat_id = msg['user_id']

    is_group_chat = chat_id >= GROUP_CHAT_MIN_ID
    if is_group_chat:
        title = msg['title']
    else:
        user_id = msg.get('user_id') or msg.get('from_id')
        assert user_id is not None
        user = udict[user_id]
        title = f'{user.first_name} {user.last_name}'
    return Chat(
        chat_id=chat_id,
        title=title,
    )


def _parse_msg(*, msg: Json, chat: Chat, udict: Users) -> Message:
    mid = msg['id']
    md = msg['date']

    dt = datetime.fromtimestamp(md, tz=TZ)

    # todo attachments? e.g. url could be an attachment
    # todo might be forwarded?
    mb = msg.get('body')
    if mb is None:
        mb = msg.get('text')
    assert mb is not None, msg

    out = msg['out'] == 1
    if out:
        user = udict[config.user_id]
    else:
        mu = msg.get('user_id') or msg.get('from_id')
        assert mu is not None, msg
        user = udict[mu]
    return Message(
        dt=dt,
        chat=chat,
        id=mid,
        user=user,
        body=mb,
    )


def _messages() -> Iterator[Res[Message]]:
    udict = users()

    uchats = get_files(config.storage_path, glob='userchat_*.json') + get_files(config.storage_path, glob='groupchat_*.json')
    for f in uchats:
        j = json.loads(f.read_text())
        # ugh. very annoying, sometimes not possible to extract title from last message
        # due to newer api...
        # so just do in defensively until we succeed...
        chat = None
        ex = None
        for m in reversed(j):
            try:
                chat = _parse_chat(msg=m, udict=udict)
            except Exception as e:
                ex = e
                continue
        if chat is None:
            assert ex is not None
            yield ex
            continue

        for msg in j:
            try:
                yield _parse_msg(msg=msg, chat=chat, udict=udict)
            except Exception as e:
                yield e


def messages() -> Iterator[Res[Message]]:
    # seems that during backup messages were sometimes duplicated..
    yield from unique_everseen(_messages)


def stats() -> Stats:
    return {
        **stat(users),
        **stat(messages),
    }
