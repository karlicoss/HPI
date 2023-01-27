"""
Converts IP addresses provided by my.location.ip to estimated locations
"""

REQUIRES = ["git+https://github.com/seanbreckenridge/ipgeocache"]

from my.core import dataclass, Stats
from my.config import location


@dataclass
class config(location.via_ip):
    # no real science to this, just a guess of ~15km accuracy for IP addresses
    accuracy: float = 15_000.0


from typing import Iterator

from .common import Location
from my.ip.all import ips


def locations() -> Iterator[Location]:
    for ip in ips():
        loc: str = ip.ipgeocache()["loc"]
        lat, _, lon = loc.partition(",")
        yield Location(
            lat=float(lat),
            lon=float(lon),
            dt=ip.dt,
            accuracy=config.accuracy,
            elevation=None,
        )


def stats() -> Stats:
    from my.core import stat

    return {**stat(locations)}
