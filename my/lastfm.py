'''
Last.fm scrobbles
'''

from .core import Paths, dataclass
from my.config import lastfm as user_config

@dataclass
class lastfm(user_config):
    """
    Uses [[https://github.com/karlicoss/lastfm-backup][lastfm-backup]] outputs
    """
    export_path: Paths


from .core.cfg import make_config
config = make_config(lastfm)


from datetime import datetime
import json
from pathlib import Path
from typing import NamedTuple, Sequence, Iterable

import pytz

from .core.common import mcachew, Json, get_files


def inputs() -> Sequence[Path]:
    return get_files(config.export_path)


# TODO memoised properties?
# TODO lazy mode and eager mode?
# lazy is a bit nicer in terms of more flexibility and less processing?
# eager is a bit more explicit for error handling


class Scrobble(NamedTuple):
    raw: Json

    # TODO mm, no timezone? hopefully it's UTC
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


@mcachew(depends_on=inputs)
def scrobbles() -> Iterable[Scrobble]:
    last = max(inputs())
    j = json.loads(last.read_text())

    for raw in reversed(j):
        yield Scrobble(raw=raw)


from .core import stat, Stats
def stats() -> Stats:
    return stat(scrobbles)


def fill_influxdb() -> None:
    from .core import influxdb
    # todo needs to be more automatic
    sd = (dict(
        dt=x.dt,
        track=x.track,
    ) for x in scrobbles())
    influxdb.fill(sd, measurement=__name__)
