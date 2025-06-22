"""
To test my.location.fallback_location.all
"""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from more_itertools import ilen

import my.ip.all as ip_module
from my.ip.common import IP
from my.location.fallback import via_ip

from ..shared_tz_config import config  # autoused fixture


# these are all tests for the bisect algorithm defined in via_ip.py
# to make sure we can correctly find IPs that are within the 'for_duration' of a given datetime
def test_ip_fallback() -> None:
    # precondition, make sure that the data override works
    assert ilen(ip_module.ips()) == ilen(data())
    assert ilen(ip_module.ips()) == ilen(via_ip.fallback_locations())
    assert ilen(via_ip.fallback_locations()) == 5
    assert ilen(via_ip._sorted_fallback_locations()) == 5

    # confirm duration from via_ip since that is used for bisect
    assert via_ip.config.for_duration == timedelta(hours=24)

    # basic tests

    # try estimating slightly before the first IP
    est = list(via_ip.estimate_location(datetime(2020, 1, 1, 11, 59, 59, tzinfo=timezone.utc)))
    assert len(est) == 0

    # during the duration for the first IP
    est = list(via_ip.estimate_location(datetime(2020, 1, 1, 12, 30, 0, tzinfo=timezone.utc)))
    assert len(est) == 1

    # right after the 'for_duration' for an IP
    est = list(
        via_ip.estimate_location(datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + via_ip.config.for_duration + timedelta(seconds=1))
    )
    assert len(est) == 0

    # on 2/1/2020, threes one IP if before 16:30
    est = list(via_ip.estimate_location(datetime(2020, 2, 1, 12, 30, 0, tzinfo=timezone.utc)))
    assert len(est) == 1

    # and two if after 16:30
    est = list(via_ip.estimate_location(datetime(2020, 2, 1, 17, 00, 0, tzinfo=timezone.utc)))
    assert len(est) == 2

    # the 12:30 IP should 'expire' before the 16:30 IP, use 3:30PM on the next day
    est = list(via_ip.estimate_location(datetime(2020, 2, 2, 15, 30, 0, tzinfo=timezone.utc)))
    assert len(est) == 1

    use_dt = datetime(2020, 3, 1, 12, 15, 0, tzinfo=timezone.utc)

    # test last IP
    est = list(via_ip.estimate_location(use_dt))
    assert len(est) == 1

    # datetime should be the IPs, not the passed IP (if via_home, it uses the passed dt)
    assert est[0].dt != use_dt

    # test interop with other fallback estimators/all.py
    #
    # redefine fallback_estimators to prevent possible namespace packages the user
    # may have installed from having side effects testing this
    from my.location.fallback import all, via_home  # noqa: A004

    def _fe() -> Iterator[all.LocationEstimator]:
        yield via_ip.estimate_location
        yield via_home.estimate_location

    all.fallback_estimators = _fe
    assert ilen(all.fallback_estimators()) == 2

    # test that all.estimate_location has access to both IPs
    #
    # just passing via_ip should give one IP
    from my.location.fallback.common import _iter_estimate_from

    raw_est = list(_iter_estimate_from(use_dt, (via_ip.estimate_location,)))
    assert len(raw_est) == 1
    assert raw_est[0].datasource == "via_ip"
    assert raw_est[0].accuracy == 15_000

    # passing home should give one
    home_est = list(_iter_estimate_from(use_dt, (via_home.estimate_location,)))
    assert len(home_est) == 1
    assert home_est[0].accuracy == 30_000

    # make sure ip accuracy is more accurate
    assert raw_est[0].accuracy < home_est[0].accuracy

    # passing both should give two
    raw_est = list(_iter_estimate_from(use_dt, (via_ip.estimate_location, via_home.estimate_location)))
    assert len(raw_est) == 2

    # shouldn't raise value error
    all_est = all.estimate_location(use_dt)
    # should have used the IP from via_ip since it was more accurate
    assert all_est.datasource == "via_ip"

    # test that a home defined in shared_tz_config.py is used if no IP is found
    loc = all.estimate_location(datetime(2021, 1, 1, 12, 30, 0, tzinfo=timezone.utc))
    assert loc.datasource == "via_home"

    # test a different home using location.fallback.all
    bulgaria = all.estimate_location(datetime(2006, 1, 1, 12, 30, 0, tzinfo=timezone.utc))
    assert bulgaria.datasource == "via_home"
    assert (bulgaria.lat, bulgaria.lon) == (42.697842, 23.325973)
    assert (loc.lat, loc.lon) != (bulgaria.lat, bulgaria.lon)


def data() -> Iterator[IP]:
    # random IP addresses
    yield IP(addr="67.98.113.0", dt=datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    yield IP(addr="67.98.112.0", dt=datetime(2020, 1, 15, 12, 0, 0, tzinfo=timezone.utc))
    yield IP(addr="59.40.113.87", dt=datetime(2020, 2, 1, 12, 0, 0, tzinfo=timezone.utc))
    yield IP(addr="59.40.139.87", dt=datetime(2020, 2, 1, 16, 0, 0, tzinfo=timezone.utc))
    yield IP(addr="161.235.192.228", dt=datetime(2020, 3, 1, 12, 0, 0, tzinfo=timezone.utc))


@pytest.fixture(autouse=True)
def prepare(config):
    before = ip_module.ips
    # redefine the my.ip.all function using data for testing
    ip_module.ips = data
    try:
        yield
    finally:
        ip_module.ips = before
