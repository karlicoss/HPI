"""
Converts IP addresses provided by my.location.ip to estimated locations
"""

REQUIRES = ["git+https://github.com/purarue/ipgeocache"]

from dataclasses import dataclass
from datetime import timedelta

from my.config import location
from my.core import Stats, make_config
from my.core.warnings import medium


@dataclass
class ip_config(location.via_ip):
    # no real science to this, just a guess of ~15km accuracy for IP addresses
    accuracy: float = 15_000.0
    # default to being accurate for a day
    for_duration: timedelta = timedelta(hours=24)


# TODO: move config to location.fallback.via_location instead and add migration
config = make_config(ip_config)


from collections.abc import Iterator
from functools import lru_cache

from my.core import make_logger
from my.core.compat import bisect_left
from my.location.common import Location
from my.location.fallback.common import DateExact, FallbackLocation, _datetime_timestamp

logger = make_logger(__name__, level="warning")


def fallback_locations() -> Iterator[FallbackLocation]:
    # prefer late import since ips get overridden in tests
    from my.ip.all import ips

    dur = config.for_duration.total_seconds()
    for ip in ips():
        lat, lon = ip.latlon
        yield FallbackLocation(
            lat=lat,
            lon=lon,
            dt=ip.dt,
            accuracy=config.accuracy,
            duration=dur,
            elevation=None,
            datasource="via_ip",
        )


# for compatibility with my.location.via_ip, this shouldn't be used by other modules
def locations() -> Iterator[Location]:
    medium("locations is deprecated, should use fallback_locations or estimate_location")
    yield from map(FallbackLocation.to_location, fallback_locations())


@lru_cache(1)
def _sorted_fallback_locations() -> list[FallbackLocation]:
    fl = list(filter(lambda l: l.duration is not None, fallback_locations()))
    logger.debug(f"Fallback locations: {len(fl)}, sorting...:")
    fl.sort(key=lambda l: l.dt.timestamp())
    return fl


def estimate_location(dt: DateExact) -> Iterator[FallbackLocation]:
    # logger.debug(f"Estimating location for: {dt}")
    fl = _sorted_fallback_locations()
    dt_ts = _datetime_timestamp(dt)

    # search to find the first possible location which contains dt (something that started up to
    # config.for_duration ago, and ends after dt)
    idx = bisect_left(fl, dt_ts - config.for_duration.total_seconds(), key=lambda l: l.dt.timestamp())

    # all items are before the given dt
    if idx == len(fl):
        return

    # iterate through in sorted order, until we find a location that is after the given dt
    while idx < len(fl):
        loc = fl[idx]
        start_time = loc.dt.timestamp()
        # loc.duration is filtered for in _sorted_fallback_locations
        end_time = start_time + loc.duration  # type: ignore[operator]
        if start_time <= dt_ts <= end_time:
            # logger.debug(f"Found location for {dt}: {loc}")
            yield loc
        # no more locations could possibly contain dt
        if start_time > dt_ts:
            # logger.debug(f"Passed start time: {end_time} > {dt_ts} ({datetime.fromtimestamp(end_time)} > {datetime.fromtimestamp(dt_ts)})")
            break
        idx += 1


def stats() -> Stats:
    from my.core import stat

    return {**stat(locations)}
