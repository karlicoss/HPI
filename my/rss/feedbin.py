"""
Feedbin RSS reader
"""

import json
from pathlib import Path
from typing import Iterator, Sequence

from my.core import get_files, stat, Stats
from my.core.compat import fromisoformat
from .common import Subscription, SubscriptionState

from my.config import feedbin as config


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


def parse_file(f: Path) -> Iterator[Subscription]:
    raw = json.loads(f.read_text())
    for r in raw:
        yield Subscription(
            created_at=fromisoformat(r['created_at']),
            title=r['title'],
            url=r['site_url'],
            id=r['id'],
        )


def states() -> Iterator[SubscriptionState]:
    for f in inputs():
        # TODO ugh. depends on my naming. not sure if useful?
        dts = f.stem.split('_')[-1]
        dt = fromisoformat(dts)
        subs = list(parse_file(f))
        yield dt, subs


def stats() -> Stats:
    return stat(states)
