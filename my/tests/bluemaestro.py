from collections.abc import Iterator

import pytest
from more_itertools import one

from my.bluemaestro import Measurement, measurements
from my.core.cfg import tmp_config

from .common import testdata


def ok_measurements() -> Iterator[Measurement]:
    for m in measurements():
        assert not isinstance(m, Exception)
        yield m


def test() -> None:
    res2020 = [m for m in ok_measurements() if '2020' in str(m.dt)]

    tp = [x for x in res2020 if x.temp == 2.1]
    assert len(tp) > 0
    for p in tp:
        print(p)
        dts = p.dt.strftime('%Y%m%d %H')
        # check that timezone is set properly
        assert dts == '20200824 22'

    assert len(tp) == 1  # should be unique

    # 2.5 K + 4 K datapoints, somewhat overlapping
    assert len(res2020) < 6000


def test_old_db() -> None:
    res = list(ok_measurements())

    r1 = one(x for x in res if x.dt.strftime('%Y%m%d %H:%M:%S') == '20181003 09:07:00')
    r2 = one(x for x in res if x.dt.strftime('%Y%m%d %H:%M:%S') == '20181003 09:19:00')

    assert r1.temp == 16.8
    assert r2.temp == 18.5
    assert r1.pressure == 1024.5
    assert r2.pressure == 1009.8


@pytest.fixture(autouse=True)
def prepare():
    bmdata = testdata() / 'hpi-testdata' / 'bluemaestro'
    assert bmdata.exists(), bmdata

    class bluemaestro:
        export_path = bmdata

    with tmp_config() as config:
        config.bluemaestro = bluemaestro
        yield
