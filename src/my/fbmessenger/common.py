from __future__ import annotations

from my.core import __NOT_HPI_MODULE__  # isort: skip

from collections.abc import Iterator
from typing import Protocol

from my.core import datetime_aware


class Thread(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str | None: ...


class Sender(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def name(self) -> str | None: ...


class Message(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def dt(self) -> datetime_aware: ...

    @property
    def text(self) -> str | None: ...

    @property
    def thread(self) -> Thread: ...

    @property
    def sender(self) -> Sender: ...


from itertools import chain

from more_itertools import unique_everseen

from my.core import Res, warn_if_empty


@warn_if_empty
def _merge_messages(*sources: Iterator[Res[Message]]) -> Iterator[Res[Message]]:
    # todo might be nice to dump some stats for debugging, e.g. how many were overlapping?
    def key(r: Res[Message]):
        if isinstance(r, Exception):
            return str(r)
        else:
            # use both just in case, would be easier to spot tz issues
            # similar to twitter, might make sense to generify/document as a pattern
            return (r.id, r.dt)
    yield from unique_everseen(chain(*sources), key=key)


# TODO some notes about gdpr export (since there is no module yet)
# ugh, messages seem to go from new to old in messages_N.json files as N increases :facepalm:
# seems like it's storing local timestamp :facepalm:
# checked against a message sent on 4 may 2022
