from datetime import datetime
from itertools import chain
from typing import Iterator

from my.core import warn_if_empty, Res
from my.core.compat import Protocol

from more_itertools import unique_everseen


class Message(Protocol):
    created: datetime
    text: str
    # TODO add some sort of thread id


@warn_if_empty
def _merge_messages(*sources: Iterator[Res[Message]]) -> Iterator[Res[Message]]:
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
    return unique_everseen(chain(*sources), key=key)
