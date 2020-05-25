"""
Feedbin RSS reader
"""

from my.config import feedbin as config

from pathlib import Path
from typing import Sequence

from ..core.common import listify, get_files, isoparse
from .common import Subscription


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


import json

@listify
def parse_file(f: Path):
    raw = json.loads(f.read_text())
    for r in raw:
        yield Subscription(
            created_at=isoparse(r['created_at']),
            title=r['title'],
            url=r['site_url'],
            id=r['id'],
        )


from typing import Iterable
from .common import SubscriptionState
def states() -> Iterable[SubscriptionState]:
    # meh
    from dateutil.parser import isoparse # type: ignore
    for f in inputs():
        # TODO ugh. depends on my naming. not sure if useful?
        dts = f.stem.split('_')[-1]
        dt = isoparse(dts)
        subs = parse_file(f)
        yield dt, subs


def stats():
    from more_itertools import ilen, last
    return {
        'subscriptions': ilen(last(states())[1])
    }
