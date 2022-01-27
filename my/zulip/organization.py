"""
Zulip data from [[https://memex.zulipchat.com/help/export-your-organization][Organization export]]
"""
from dataclasses import dataclass
from typing import Sequence, Iterator, Dict

from my.config import zulip as user_config

from ..core import Paths
@dataclass
class organization(user_config.organization):
    # paths[s]/glob to the exported JSON data
    export_path: Paths


from pathlib import Path
from ..core import get_files, Json
def inputs() -> Sequence[Path]:
    return get_files(organization.export_path)


from datetime import datetime
@dataclass(frozen=True)
class Message:
    id: int
    sent: datetime
    subject: str
    sender: str
    content: str  # TODO hmm, it keeps markdown, not sure how/whether it's worth to prettify at all?
    # TODO recipient??
    # todo keep raw item instead? not sure


# TODO hmm kinda unclear whether it uses UTC or not??
# https://github.com/zulip/zulip/blob/0c2e4eec200d986a9a020f3e9a651d27216e0e85/zerver/models.py#L3071-L3076
# it keeps it tz aware.. but not sure what happens after?
# https://github.com/zulip/zulip/blob/1dfddffc8dac744fd6a6fbfd937018074c8bb166/zproject/computed_settings.py#L151


from itertools import count
import json
from ..core.error import Res
from ..core.kompress import kopen, kexists
# TODO check that it also works with unpacked dirs???
def messages() -> Iterator[Res[Message]]:
    # TODO hmm -- not sure if max lexicographically will actually be latest?
    last = max(inputs())
    no_suffix = last.name.split('.')[0]

    with kopen(last, f'{no_suffix}/realm.json') as f:
        rj = json.load(f)
    id2user: Dict[int, str] = {}
    for j in rj['zerver_userprofile']:
        id2user[j['id']] = j['full_name']
    for j in rj['zerver_userprofile_crossrealm']:  # e.g. zulip bot
        id2user[j['id']] = j['email']

    def _parse_message(j: Json) -> Message:
        ds = j['date_sent']
        return Message(
            id      = j['id'],
            sent    = datetime.fromtimestamp(ds),
            subject = j['subject'],
            sender  = id2user[j['sender']],
            content = j['content'],
        )

    for idx in count(start=1, step=1):
        fname = f'messages-{idx:06}.json'
        fpath = f'{no_suffix}/{fname}'
        if not kexists(last, fpath):
            break
        with kopen(last, fpath) as f:
            mj = json.load(f)
        # TODO handle  zerver_usermessage
        for j in mj['zerver_message']:
            try:
                yield _parse_message(j)
            except Exception as e:
                yield e
