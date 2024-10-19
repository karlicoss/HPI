'''
Simple location provider, serving as a fallback when more detailed data isn't available
'''

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timezone
from functools import cache
from typing import cast

from my.config import location as user_config
from my.location.common import DateIsh, LatLon
from my.location.fallback.common import DateExact, FallbackLocation


@dataclass
class Config(user_config):
    home: LatLon | Sequence[tuple[DateIsh, LatLon]]

    # default ~30km accuracy
    # this is called 'home_accuracy' since it lives on the base location.config object,
    # to differentiate it from accuracy for other providers
    home_accuracy: float = 30_000.0

    # TODO could make current Optional and somehow determine from system settings?
    @property
    def _history(self) -> Sequence[tuple[datetime, LatLon]]:
        home1 = self.home
        # todo ugh, can't test for isnstance LatLon, it's a tuple itself
        home2: Sequence[tuple[DateIsh, LatLon]]
        if isinstance(home1[0], tuple):
            # already a sequence
            home2 = cast(Sequence[tuple[DateIsh, LatLon]], home1)
        else:
            # must be a pair of coordinates. also doesn't really matter which date to pick?
            loc = cast(LatLon, home1)
            home2 = [(datetime.min, loc)]

        # todo cache?
        res = []
        for x, loc in home2:
            dt: datetime
            if isinstance(x, str):
                dt = datetime.fromisoformat(x)
            elif isinstance(x, datetime):
                dt = x
            else:
                dt = datetime.combine(x, time.min)
            # todo not sure about doing it here, but makes it easier to compare..
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            res.append((dt, loc))
        res = sorted(res, key=lambda p: p[0])
        return res


from ...core.cfg import make_config

config = make_config(Config)


@cache
def get_location(dt: datetime) -> LatLon:
    '''
    Interpolates the location at dt
    '''
    loc = list(estimate_location(dt))
    assert len(loc) == 1
    return loc[0].lat, loc[0].lon


# TODO: in python3.8, use functools.cached_property instead?
@cache
def homes_cached() -> list[tuple[datetime, LatLon]]:
    return list(config._history)


def estimate_location(dt: DateExact) -> Iterator[FallbackLocation]:
    from my.location.fallback.common import _datetime_timestamp
    d: float = _datetime_timestamp(dt)
    hist = list(reversed(homes_cached()))
    for pdt, (lat, lon) in hist:
        if d >= pdt.timestamp():
            yield FallbackLocation(
                lat=lat,
                lon=lon,
                accuracy=config.home_accuracy,
                dt=datetime.fromtimestamp(d, timezone.utc),
                datasource='via_home')
            return

    # I guess the most reasonable is to fallback on the first location
    lat, lon = hist[-1][1]
    yield FallbackLocation(
        lat=lat,
        lon=lon,
        accuracy=config.home_accuracy,
        dt=datetime.fromtimestamp(d, timezone.utc),
        datasource='via_home')
