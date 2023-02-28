"""
Provides location/timezone data from IP addresses, using [[https://github.com/seanbreckenridge/ipgeocache][ipgeocache]]
"""

from my.core import __NOT_HPI_MODULE__

import ipaddress
from typing import NamedTuple, Iterator, Tuple
from datetime import datetime

import ipgeocache

from my.core import Json


class IP(NamedTuple):
    dt: datetime
    addr: str  # an IP address

    # TODO: could cache? not sure if it's worth it
    def ipgeocache(self) -> Json:
        return ipgeocache.get(self.addr)

    @property
    def latlon(self) -> Tuple[float, float]:
        loc: str = self.ipgeocache()["loc"]
        lat, _, lon = loc.partition(",")
        return float(lat), float(lon)

    @property
    def tzname(self) -> str:
        tz: str = self.ipgeocache()["timezone"]
        return tz


def drop_private(ips: Iterator[IP]) -> Iterator[IP]:
    """
    Helper function that can be used to filter out private IPs
    """
    for ip in ips:
        if ipaddress.ip_address(ip.addr).is_private:
            continue
        yield ip
