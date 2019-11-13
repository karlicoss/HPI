#!/usr/bin/env python3
from functools import lru_cache
from typing import Dict, List, NamedTuple
from datetime import datetime
from pathlib import Path
import os
import json

import pytz

_PATH = Path("/L/backups/lastfm")

class Scrobble(NamedTuple):
    dt: datetime
    track: str


# TODO memoise...?

# TODO watch out, if we keep the app running it might expire
def _iter_scrobbles():
    last = max(_PATH.glob('*.json'))
    # TODO mm, no timezone? wonder if it's UTC...
    j = json.loads(last.read_text())

    for d in j:
        ts = int(d['date'])
        dt = datetime.fromtimestamp(ts, tz=pytz.utc)
        track = f"{d['artist']} — {d['name']}"
        yield Scrobble(dt, track)


@lru_cache(1)
def get_scrobbles():
    return list(_iter_scrobbles())


def test():
    assert len(get_scrobbles()) > 1000
