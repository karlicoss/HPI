from . import paths
from .common import listify
from ._rss import Subscription

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from dateutil.parser import isoparse


@listify
def parse_file(f: Path):
    raw = json.loads(f.read_text())
    for r in raw:
        # err, some even don't have website..
        website = r.get('website')
        yield Subscription(
            # TODO created_at?
            title=r['title'],
            url=website,
            id=r['id'],
        )

def get_states() -> Dict[datetime, List[Subscription]]:
    res = {}
    for f in sorted(Path(paths.feedly.export_dir).glob('*.json')):
        dts = f.stem.split('_')[-1]
        dt = datetime.strptime(dts, '%Y%m%d%H%M%S')
        subs = parse_file(f)
        res[dt] = subs
    return res
