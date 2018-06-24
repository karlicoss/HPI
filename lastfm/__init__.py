from functools import lru_cache
from kython import listdir_abs, json_load, JSONType
from typing import Dict, List, NamedTuple
from pytz import UTC
from datetime import datetime
import os


_PATH = "/L/backups/lastfm"

class Scrobble(NamedTuple):
    dt: datetime
    track: str


# TODO memoise...?

# TODO watch out, if we keep the app running it might expire
def _iter_scrobbles():
    last = max(listdir_abs(_PATH))
    # TODO mm, no timezone? wonder if it's UTC...
    j: List[Dict[str, str]]
    with open(last, 'r') as fo:
        j = json_load(fo)
    for d in j:
        ts = int(d['date'])
        dt = datetime.fromtimestamp(ts, tz=UTC)
        track = f"{d['artist']} — {d['name']}"
        yield Scrobble(dt, track)


@lru_cache()
def get_scrobbles():
    return list(_iter_scrobbles())
