"""
Zulip data from [[https://memex.zulipchat.com/help/export-your-organization][Organization export]]
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
import json
from pathlib import Path
from typing import Sequence, Iterator, Dict, Union

from my.core import (
    assert_never,
    datetime_aware,
    get_files,
    stat,
    Json,
    Paths,
    Res,
    Stats,
)
from my.core.error import notnone
import my.config


@dataclass
class organization(my.config.zulip.organization):
    # paths[s]/glob to the exported JSON data
    export_path: Paths


def inputs() -> Sequence[Path]:
    # TODO: seems like export ids are kinda random..
    # not sure what's the best way to figure out the last without renaming?
    # could use mtime perhaps?
    return get_files(organization.export_path, sort=False)


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
    sent: datetime_aware  # double checked and they are in utc
    subject: str
    sender_id: int
    server_id: int
    content: str  # TODO hmm, it keeps markdown, not sure how/whether it's worth to prettify at all?
    # TODO recipient??
    # todo keep raw item instead? not sure


@dataclass(frozen=True)
class Message:
    id: int
    sent: datetime_aware
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


# todo cache it
def _entities() -> Iterator[Res[Union[Server, Sender, _Message]]]:
    last = max(inputs())

    # todo would be nice to switch it to unpacked dirs as well, similar to ZipPath
    # I guess makes sense to have a special implementation for .tar.gz considering how common are they
    import tarfile

    tfile = tarfile.open(last)

    subdir = tfile.getnames()[0]  # there is a directory inside tar file, first name should be that

    with notnone(tfile.extractfile(f'{subdir}/realm.json')) as fo:
        rj = json.load(fo)

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
            full_name=j['email'],  # doesn't seem to have anything
            email=j['email'],
        )

    def _parse_message(j: Json) -> _Message:
        ds = j['date_sent']
        # fmt: off
        return _Message(
            id        = j['id'],
            sent      = datetime.fromtimestamp(ds, tz=timezone.utc),
            subject   = j['subject'],
            sender_id = j['sender'],
            server_id = server.id,
            content   = j['content'],
        )
        # fmt: on

    for idx in count(start=1, step=1):
        fname = f'messages-{idx:06}.json'
        fpath = f'{subdir}/{fname}'
        if fpath not in tfile.getnames():
            # tarfile doesn't have .exists?
            break
        with notnone(tfile.extractfile(fpath)) as fo:
            mj = json.load(fo)
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
        assert_never(x)


def stats() -> Stats:
    return {**stat(messages)}
