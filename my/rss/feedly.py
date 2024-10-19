"""
Feedly RSS reader
"""

import json
from abc import abstractmethod
from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from my.core import Paths, get_files

from .common import Subscription, SubscriptionState


class config(Protocol):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        raise NotImplementedError


def make_config() -> config:
    from my.config import feedly as user_config

    class combined_config(user_config, config): ...

    return combined_config()


def inputs() -> Sequence[Path]:
    cfg = make_config()
    return get_files(cfg.export_path)


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
