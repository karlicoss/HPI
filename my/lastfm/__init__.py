'''
Last.fm scrobbles
'''


from ..common import get_files, mcachew, Json

from datetime import datetime
import json
from pathlib import Path
from typing import NamedTuple, Any, Sequence, Iterable

import pytz

from my.config import lastfm as config

# TODO memoised properties?
# TODO lazy mode and eager mode?
# lazy is a bit nicer in terms of more flexibility and less processing?
# eager is a bit more explicit for error handling

def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


class Scrobble(NamedTuple):
    raw: Json

    # TODO mm, no timezone? hopefuly it's UTC
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


@mcachew(hashf=lambda: inputs())
def scrobbles() -> Iterable[Scrobble]:
    last = max(inputs())
    j = json.loads(last.read_text())

    for raw in j:
        yield Scrobble(raw=raw)
