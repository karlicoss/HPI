"""
Feedbin RSS reader
"""

from my.config import feedbin as config

from pathlib import Path
from typing import Sequence

from my.core.common import listify, get_files
from my.core.compat import fromisoformat
from .common import Subscription


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


import json

@listify
def parse_file(f: Path):
    raw = json.loads(f.read_text())
    for r in raw:
        yield Subscription(
            created_at=fromisoformat(r['created_at']),
            title=r['title'],
            url=r['site_url'],
            id=r['id'],
        )


from typing import Iterable
from .common import SubscriptionState
def states() -> Iterable[SubscriptionState]:
    for f in inputs():
        # TODO ugh. depends on my naming. not sure if useful?
        dts = f.stem.split('_')[-1]
        dt = fromisoformat(dts)
        subs = parse_file(f)
        yield dt, subs


def stats():
    from more_itertools import ilen, last
    return {
        'subscriptions': ilen(last(states())[1])
    }
