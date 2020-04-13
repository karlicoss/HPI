"""
Feedly RSS reader
"""

from .common import listify
from ._rss import Subscription

from my.config import feedly as config

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import pytz


@listify
def parse_file(f: Path):
    raw = json.loads(f.read_text())
    for r in raw:
        # err, some even don't have website..
        rid = r['id']
        website = r.get('website', rid) # meh
        yield Subscription(
            # TODO created_at?
            title=r['title'],
            url=website,
            id=rid,
        )

def get_states() -> Dict[datetime, List[Subscription]]:
    res = {}
    # TODO use get_files
    for f in sorted(Path(config.export_dir).glob('*.json')):
        dts = f.stem.split('_')[-1]
        dt = datetime.strptime(dts, '%Y%m%d%H%M%S')
        dt = pytz.utc.localize(dt)
        subs = parse_file(f)
        res[dt] = subs
    return res
