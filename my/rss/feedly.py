"""
Feedly RSS reader
"""

from my.config import feedly as config

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterator, Sequence

from my.core import get_files
from .common import Subscription, SubscriptionState


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def parse_file(f: Path) -> Iterator[Subscription]:
    raw = json.loads(f.read_text())
    for r in raw:
        # err, some even don't have website..
        rid = r['id']
        website = r.get('website', rid)  # meh
        yield Subscription(
            created_at=None,
            title=r['title'],
            url=website,
            id=rid,
        )


def states() -> Iterator[SubscriptionState]:
    for f in inputs():
        dts = f.stem.split('_')[-1]
        dt = datetime.strptime(dts, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        subs = list(parse_file(f))
        yield dt, subs
