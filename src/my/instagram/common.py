from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime
from itertools import chain
from typing import Any, Protocol

from my.core import Res, warn_if_empty


class User(Protocol):
    id: str
    username: str
    full_name: str


class Message(Protocol):
    created: datetime
    text: str
    thread_id: str

    # property because it's more mypy friendly
    @property
    def user(self) -> User: ...


@warn_if_empty
def _merge_messages(*sources: Iterator[Res[Message]]) -> Iterator[Res[Message]]:
    # TODO double check it works w.r.t. naive/aware timestamps?
    def key(r: Res[Message]):
        if isinstance(r, Exception):
            # NOTE: using str() against Exception is nice so exceptions with same args are treated the same..
            return str(r)

        dt = r.created
        # seems that GDPR has millisecond resolution.. so best to strip them off when merging
        round_us = dt.microsecond // 1000 * 1000
        without_us = r.created.replace(microsecond=round_us)
        # using text as key is a bit crap.. but atm there are no better shared fields
        return (without_us, r.text)

    # ugh
    #  - in gdpr export, User objects are kinda garbage
    #  - thread ids are inconsistent even within Android databases
    #    maybe always take latest gdpr when merging??
    #  - TODO maybe always grab message ids from android? there is nothing in gdpr

    # so the only way to correlate is to try and match messages bodies/timestamps
    # we also can't use unique_everseen here, otherwise will never get a chance to unify threads

    mmap: dict[str, Message] = {}
    thread_map = {}
    user_map = {}

    for m in chain(*sources):
        if isinstance(m, Exception):
            yield m
            continue

        k = key(m)
        mm = mmap.get(k)

        if mm is not None:
            # already emitted, we get a chance to populate mappings
            if m.thread_id not in thread_map:
                thread_map[m.thread_id] = mm.thread_id
            if m.user.id not in user_map:
                user_map[m.user.id] = mm.user
        else:
            # not emitted yet, need to emit
            repls: dict[str, Any] = {}
            tid = thread_map.get(m.thread_id)
            if tid is not None:
                repls['thread_id'] = tid
            user = user_map.get(m.user.id)
            if user is not None:
                repls['user'] = user
            if len(repls) > 0:
                m = replace(m, **repls)  # type: ignore[type-var]  # ugh mypy is confused because of Protocol?
            mmap[k] = m
            yield m
