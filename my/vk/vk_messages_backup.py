'''
VK data (exported by [[https://github.com/Totktonada/vk_messages_backup][Totktonada/vk_messages_backup]])
'''
# note: could reuse the original repo, but little point I guess since VK closed their API


from datetime import datetime
import json
from typing import Dict, Iterable, NamedTuple

import pytz

from ..core import Json

from my.config import vk_messages_backup as config


Uid = str
Name = str


Users = Dict[Uid, Name]

def users() -> Users:
    # todo cache?
    files = list(sorted(config.storage_path.glob('user_*.json')))
    res = {}
    for f in files:
        j = json.loads(f.read_text())
        uid = j['id']
        uf  = j['first_name']
        ul  = j['last_name']
        res[uid] = f'{uf} {ul}'
    return res


class Message(NamedTuple):
    chat_id: str
    dt: datetime
    user: Name
    body: str


msk_tz = pytz.timezone('Europe/Moscow')
# todo hmm, vk_messages_backup used this tz? not sure if vk actually used to return this tz in api?

def _parse(x: Json, chat_id: str, udict: Users) -> Message:
    mid = x['id'] # todo not sure if useful?
    md  = x['date']

    dt = datetime.fromtimestamp(md, msk_tz)

    # todo attachments? e.g. url could be an attachment
    # todo might be forwarded?
    mb  = x.get('body')
    if mb is None:
        mb = x.get('text')
    assert mb is not None

    mu  = x.get('user_id') or x.get('peer_id')
    assert mu is not None
    out = x['out'] == 1
    # todo use name from the config?
    user = 'you' if out else udict[mu]

    # todo conversation id??

    return Message(
        chat_id=chat_id,
        dt=dt,
        user=user,
        body=mb,
    )


from ..core.error import Res
def messages() -> Iterable[Res[Message]]:
    udict = users()

    uchats = list(sorted(config.storage_path.glob('userchat_*.json' ))) + \
             list(sorted(config.storage_path.glob('groupchat_*.json')))
    for f in uchats:
        chat_id = f.stem.split('_')[-1]
        j = json.loads(f.read_text())
        for x in j:
            try:
                yield _parse(x, chat_id=chat_id, udict=udict)
            except Exception as e:
                yield e


def stats():
    from ..core import stat
    return {
        **stat(users),
        **stat(messages),
    }
