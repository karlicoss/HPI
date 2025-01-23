"""
Github events and their metadata: comments/issues/pull requests
"""

from __future__ import annotations

from my.core import __NOT_HPI_MODULE__  # isort: skip


from collections.abc import Iterable
from datetime import datetime, timezone
from typing import NamedTuple, Optional

from my.core import make_logger, warn_if_empty
from my.core.error import Res

logger = make_logger(__name__)

class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str
    link: Optional[str]
    body: Optional[str] = None
    is_bot: bool = False


Results = Iterable[Res[Event]]

@warn_if_empty
def merge_events(*sources: Results) -> Results:
    from itertools import chain
    emitted: set[tuple[datetime, str]] = set()
    for e in chain(*sources):
        if isinstance(e, Exception):
            yield e
            continue
        if e.is_bot:
            continue
        key = (e.dt, e.eid) # use both just in case
        # TODO wtf?? some minor (e.g. 1 sec) discrepancies (e.g. create repository events)
        if key in emitted:
            logger.debug('ignoring %s: %s', key, e)
            continue
        yield e
        emitted.add(key)
        # todo use unique_everseen? Might be tricky with Exception etc..


def parse_dt(s: str) -> datetime:
    # TODO isoformat?
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


# experimental way of supportint event ids... not sure
class EventIds:
    @staticmethod
    def repo_created(*, dts: str, name: str, ref_type: str, ref: str | None) -> str:
        return f'{dts}_repocreated_{name}_{ref_type}_{ref}'

    @staticmethod
    def pr(*, dts: str, action: str, url: str) -> str:
        return f'{dts}_pr{action}_{url}'
