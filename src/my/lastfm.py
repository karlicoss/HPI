'''
Last.fm scrobbles
'''

from abc import abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from my.core import Json, Paths, Stats, datetime_aware, get_files, make_logger, stat
from my.core.cachew import mcachew
from my.core.json import json_loads

logger = make_logger(__name__)


class config(Protocol):
    @property
    @abstractmethod
    def export_path(self) -> Paths:
        """
        Uses [[https://github.com/karlicoss/lastfm-backup][lastfm-backup]] outputs
        """
        raise NotImplementedError


def make_config() -> config:
    from my.config import lastfm as user_config

    class combined_config(user_config, config): ...

    return combined_config()


def inputs() -> Sequence[Path]:
    cfg = make_config()
    return get_files(cfg.export_path)


# TODO memoised properties?
# TODO lazy mode and eager mode?
# lazy is a bit nicer in terms of more flexibility and less processing?
# eager is a bit more explicit for error handling


@dataclass
class Scrobble:
    raw: Json

    @property
    def dt(self) -> datetime_aware:
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


def stats() -> Stats:
    return stat(scrobbles)


def fill_influxdb() -> None:
    from my.core import influxdb

    # todo needs to be more automatic
    sd = (
        {
            'dt': x.dt,
            'track': x.track,
        }
        for x in scrobbles()
    )
    influxdb.fill(sd, measurement=__name__)
