"""
Github events and their metadata: comments/issues/pull requests
"""
from ..core import __NOT_HPI_MODULE__


from datetime import datetime
from typing import Optional, NamedTuple, Iterable, Set, Tuple

import pytz

from ..core import warn_if_empty, LazyLogger
from ..core.error import Res


logger = LazyLogger(__name__)

class Event(NamedTuple):
    dt: datetime
    summary: str
    eid: str
    link: Optional[str]
    body: Optional[str]=None
    is_bot: bool = False


Results = Iterable[Res[Event]]

@warn_if_empty
def merge_events(*sources: Results) -> Results:
    from itertools import chain
    emitted: Set[Tuple[datetime, str]] = set()
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
    return pytz.utc.localize(datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ'))


# experimental way of supportint event ids... not sure
class EventIds:
    @staticmethod
    def repo_created(*, dts: str, name: str, ref_type: str, ref: Optional[str]) -> str:
        return f'{dts}_repocreated_{name}_{ref_type}_{ref}'

    @staticmethod
    def pr(*, dts: str, action: str, url: str) -> str:
        return f'{dts}_pr{action}_{url}'
