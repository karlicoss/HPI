'''
Last.fm scrobbles
'''

from .. import init

from functools import lru_cache
from typing import NamedTuple, Dict, Any
from datetime import datetime
from pathlib import Path
import json

import pytz

from my.config import lastfm as config

# TODO Json type?
# TODO memoised properties?
# TODO lazy mode and eager mode?
# lazy is a bit nicer in terms of more flexibility and less processing?
# eager is a bit more explicit for error handling

class Scrobble(NamedTuple):
    raw: Dict[str, Any]

    @property
    def dt(self) -> datetime:
        ts = int(self.raw['date'])
        return datetime.fromtimestamp(ts, tz=pytz.utc)

    @property
    def artist(self) -> str:
        return self.raw['artist']

    @property
    def name(self) -> str:
        return self.raw['name']

    @property
    def track(self) -> str:
        return f'{self.artist} — {self.name}'


    # TODO __repr__, __str__
    # TODO could also be nice to make generic? maybe even depending on eagerness


# TODO memoise...?
# TODO watch out, if we keep the app running it might expire
def _iter_scrobbles():
    # TODO use get_files
    last = max(Path(config.export_path).glob('*.json'))
    # TODO mm, no timezone? hopefuly it's UTC
    j = json.loads(last.read_text())

    for raw in j:
        yield Scrobble(raw=raw)


@lru_cache(1)
def get_scrobbles():
    return list(sorted(_iter_scrobbles(), key=lambda s: s.dt))


def test():
    assert len(get_scrobbles()) > 1000
