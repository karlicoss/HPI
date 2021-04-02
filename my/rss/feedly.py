"""
Feedly RSS reader
"""

from my.config import feedly as config

from pathlib import Path
from typing import Sequence

from ..core.common import listify, get_files
from .common import Subscription


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


import json


@listify
def parse_file(f: Path):
    raw = json.loads(f.read_text())
    for r in raw:
        # err, some even don't have website..
        rid = r['id']
        website = r.get('website', rid) # meh
        yield Subscription(
            created_at=None,
            title=r['title'],
            url=website,
            id=rid,
        )


from datetime import datetime
from typing import Iterable
from .common import SubscriptionState
def states() -> Iterable[SubscriptionState]:
    import pytz
    for f in inputs():
        dts = f.stem.split('_')[-1]
        dt = datetime.strptime(dts, '%Y%m%d%H%M%S')
        dt = pytz.utc.localize(dt)
        subs = parse_file(f)
        yield dt, subs
