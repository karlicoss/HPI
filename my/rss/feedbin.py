"""
Feedbin RSS reader
"""

from my.config import feedbin as config

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
        yield Subscription(
            created_at=isoparse(r['created_at']),
            title=r['title'],
            url=r['site_url'],
            id=r['id'],
        )


def get_states() -> Dict[datetime, List[Subscription]]:
    # meh
    from dateutil.parser import isoparse # type: ignore
    res = {}
    for f in inputs():
        # TODO ugh. depends on my naming. not sure if useful?
        dts = f.stem.split('_')[-1]
        dt = isoparse(dts)
        subs = parse_file(f)
        res[dt] = subs
    return res
