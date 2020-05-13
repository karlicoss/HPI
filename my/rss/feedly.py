"""
Feedly RSS reader
"""

from my.config import feedly as config

from pathlib import Path
from typing import Sequence

from ..core.common import listify, get_files, isoparse
from ._rss import Subscription


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


import json
from typing import Dict, List
from datetime import datetime


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


def get_states() -> Dict[datetime, List[Subscription]]:
    import pytz
    res = {}
    for f in inputs():
        dts = f.stem.split('_')[-1]
        dt = datetime.strptime(dts, '%Y%m%d%H%M%S')
        dt = pytz.utc.localize(dt)
        subs = parse_file(f)
        res[dt] = subs
        # TODO get rid of these dts...
    return res
