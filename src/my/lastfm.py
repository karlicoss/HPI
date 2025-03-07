'''
Last.fm scrobbles
'''

from dataclasses import dataclass

from my.config import lastfm as user_config
from my.core import Json, Paths, datetime_aware, get_files, make_logger
from my.core.json import json_loads

logger = make_logger(__name__)


@dataclass
class lastfm(user_config):
    """
    Uses [[https://github.com/karlicoss/lastfm-backup][lastfm-backup]] outputs
    """
    export_path: Paths


from my.core.cfg import make_config

config = make_config(lastfm)


from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from my.core.cachew import mcachew


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
        return datetime.fromtimestamp(ts, tz=timezone.utc)

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
    logger.info(f'loading data from {last}')
    j = json_loads(last.read_bytes())

    for raw in reversed(j):
        yield Scrobble(raw=raw)


from my.core import Stats, stat


def stats() -> Stats:
    return stat(scrobbles)


def fill_influxdb() -> None:
    from my.core import influxdb

    # todo needs to be more automatic
    sd = ({
        'dt': x.dt,
        'track': x.track,
    } for x in scrobbles())
    influxdb.fill(sd, measurement=__name__)
