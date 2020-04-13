"""
Feedbin RSS reader
"""

from .common import listify
from ._rss import Subscription

from my.config import feedbin as config

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from dateutil.parser import isoparse


@listify
def parse_file(f: Path):
    raw = json.loads(f.read_text())
    for r in raw:
        yield Subscription(
            # TODO created_at?
            title=r['title'],
            url=r['site_url'],
            id=r['id'],
        )

def get_states() -> Dict[datetime, List[Subscription]]:
    res = {}
    # TODO use get_files
    for f in sorted(Path(config.export_dir).glob('*.json')):
        dts = f.stem.split('_')[-1]
        dt = isoparse(dts)
        subs = parse_file(f)
        res[dt] = subs
    return res
