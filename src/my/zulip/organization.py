"""
Zulip data from [[https://memex.zulipchat.com/help/export-your-organization][Organization export]]
"""

from __future__ import annotations

import json
from abc import abstractmethod
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from pathlib import Path

from my.core import (
    Json,
    Paths,
    Res,
    Stats,
    assert_never,
    datetime_aware,
    get_files,
    make_logger,
    stat,
    warnings,
)

logger = make_logger(__name__)


class config:
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """paths[s]/glob to the exported JSON data"""
        raise NotImplementedError


def make_config() -> config:
    from my.config import zulip as user_config

    class combined_config(user_config.organization, config):
        pass

    return combined_config()


def inputs() -> Sequence[Path]:
    # TODO: seems like export ids are kinda random..
    # not sure what's the best way to figure out the last without renaming?
    # could use mtime perhaps?
    return get_files(make_config().export_path, sort=False)


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
def _entities() -> Iterator[Res[Server | Sender | _Message]]:
    last = max(inputs())

    logger.info(f'extracting data from {last}')

    root: Path | None = None

    if last.is_dir():  # if it's already CPath, this will match it
        root = last
    else:
        try:
            from kompress import CPath

            root = CPath(last)
            assert len(list(root.iterdir())) > 0  # trigger to check if we have the kompress version with targz support
        except Exception as e:
            logger.exception(e)
            warnings.high("Upgrade 'kompress' to latest version with native .tar.gz support. Falling back to unpacking to tmp dir.")

    if root is None:
        from my.core.structure import match_structure

        with match_structure(last, expected=()) as res:  # expected=() matches it regardless any patterns
            [root] = res
            yield from _process_one(root)
    else:
        yield from _process_one(root)


def _process_one(root: Path) -> Iterator[Res[Server | Sender | _Message]]:
    [subdir] = root.iterdir()  # there is a directory inside tar file, first name should be that

    rj = json.loads((subdir / 'realm.json').read_text())

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
        fpath = subdir / fname
        if not fpath.exists():
            break
        mj = json.loads(fpath.read_text())
        # TODO handle  zerver_usermessage
        for j in mj['zerver_message']:
            try:
                yield _parse_message(j)
            except Exception as e:
                yield e


def messages() -> Iterator[Res[Message]]:
    id2sender: dict[int, Sender] = {}
    id2server: dict[int, Server] = {}
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
