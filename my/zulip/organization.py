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
class Server:
    id: int
    string_id: str
    name: str


@dataclass(frozen=True)
class Sender:
    id: int
    # todo make optional?
    full_name: str
    email: str


# from the data, seems that subjects are completely implicit and determined by name?
# streams have ids (can extract from realm/zerver_stream), but unclear how to correlate messages/topics to streams?

@dataclass(frozen=True)
class _Message:
    # todo hmm not sure what would be a good field order..
    id: int
    sent: datetime
    # TODO hmm kinda unclear whether it uses UTC or not??
    # https://github.com/zulip/zulip/blob/0c2e4eec200d986a9a020f3e9a651d27216e0e85/zerver/models.py#L3071-L3076
    # it keeps it tz aware.. but not sure what happens after?
    # https://github.com/zulip/zulip/blob/1dfddffc8dac744fd6a6fbfd937018074c8bb166/zproject/computed_settings.py#L151
    subject: str
    sender_id: int
    server_id: int
    content: str  # TODO hmm, it keeps markdown, not sure how/whether it's worth to prettify at all?
    # TODO recipient??
    # todo keep raw item instead? not sure


@dataclass(frozen=True)
class Message:
    id: int
    sent: datetime
    subject: str
    sender: Sender
    server: Server
    content: str

    @property
    def permalink(self) -> str:
        # seems that these link to the same message
        # https://memex.zulipchat.com/#narrow/stream/284580-python/topic/py-spy.20profiler/near/234798881
        # https://memex.zulipchat.com/#narrow/stream/284580/near/234798881
        # https://memex.zulipchat.com/#narrow/near/234798881
        # however not sure how to correlate stream id and message/topic for now, so preferring the latter version
        return f'https://{self.server.string_id}.zulipchat.com/#narrow/near/{self.id}'


from typing import Union
from itertools import count
import json
from ..core.error import Res
from ..core.kompress import kopen, kexists
# TODO cache it
def _entities() -> Iterator[Res[Union[Server, Sender, _Message]]]:
    # TODO hmm -- not sure if max lexicographically will actually be latest?
    last = max(inputs())
    no_suffix = last.name.split('.')[0]

    # TODO check that it also works with unpacked dirs???
    with kopen(last, f'{no_suffix}/realm.json') as f:
        rj = json.load(f)

    [sj] = rj['zerver_realm']
    server = Server(
        id=sj['id'],
        string_id=sj['string_id'],
        name=sj['name'],
    )
    yield server

    for j in rj['zerver_userprofile']:
        yield Sender(
            id=j['id'],
            full_name=j['full_name'],
            email=j['email'],
        )

    for j in rj['zerver_userprofile_crossrealm']:  # e.g. zulip bot
        yield Sender(
            id=j['id'],
            full_name=j['email'], # doesn't seem to have anything
            email=j['email'],
        )

    def _parse_message(j: Json) -> _Message:
        ds = j['date_sent']
        return _Message(
            id        = j['id'],
            sent      = datetime.fromtimestamp(ds),
            subject   = j['subject'],
            sender_id = j['sender'],
            server_id = server.id,
            content   = j['content'],
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


def messages() -> Iterator[Res[Message]]:
    id2sender: Dict[int, Sender] = {}
    id2server: Dict[int, Server] = {}
    for x in _entities():
        if isinstance(x, Exception):
            yield x
            continue
        if isinstance(x, Server):
            id2server[x.id] = x
            continue
        if isinstance(x, Sender):
            id2sender[x.id] = x
            continue
        if isinstance(x, _Message):
            # TODO a bit copypasty... wonder if possible to mixin or something instead
            yield Message(
                id=x.id,
                sent=x.sent,
                subject=x.subject,
                sender=id2sender[x.sender_id],
                server=id2server[x.server_id],
                content=x.content,
            )
            continue
        assert False # should be unreachable
