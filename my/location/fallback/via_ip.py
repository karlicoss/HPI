"""
Converts IP addresses provided by my.location.ip to estimated locations
"""

REQUIRES = ["git+https://github.com/seanbreckenridge/ipgeocache"]

from my.core import dataclass, Stats
from my.config import location
from my.core.warnings import medium
from datetime import datetime


@dataclass
class config(location.via_ip):
    # no real science to this, just a guess of ~15km accuracy for IP addresses
    accuracy: float = 15_000.0
    # default to being accurate for ~10 minutes
    for_duration: float = 60 * 10


from typing import Iterator

from ..common import Location
from .common import FallbackLocation
from my.ip.all import ips


def fallback_locations() -> Iterator[FallbackLocation]:
    for ip in ips():
        lat, lon = ip.latlon
        yield FallbackLocation(
            lat=lat,
            lon=lon,
            dt=ip.dt,
            accuracy=config.accuracy,
            duration=config.for_duration,
            elevation=None,
            datasource="ip",
        )


# for compatibility with my.location.via_ip, this shouldnt be used by other modules
def locations() -> Iterator[Location]:
    medium("locations is deprecated, should use fallback_locations or estimate_location")
    yield from map(FallbackLocation.to_location, fallback_locations())


def estimate_location(dt: datetime) -> Location:
    raise NotImplementedError("not implemented yet")


def stats() -> Stats:
    from my.core import stat

    return {**stat(locations)}
