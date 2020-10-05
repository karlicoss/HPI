#!/usr/bin/env python3
from pathlib import Path

from more_itertools import one

import pytest # type: ignore


def test() -> None:
    from my.bluemaestro import measurements
    res = list(measurements())

    tp = [x for x in res if x.temp == 2.1]
    assert len(tp) > 0
    for p in tp:
        print(p)
        dts = p.dt.strftime('%Y%m%d %H')
        # check that timezone is set properly
        assert dts == '20200824 22'

    assert len(tp) == 1 # should be unique

    # 2.5 K + 4 K datapoints, somwhat overlapping
    assert len(res) < 6000


@pytest.mark.skip(reason='todo add old database to the testdata')
def test_old_db() -> None:
    from my.bluemaestro import measurements
    res = list(measurements())

    r1 = one(x for x in res if x.dt.strftime('%Y%m%d %H:%M:%S') == '20181003 09:07:00')
    r2 = one(x for x in res if x.dt.strftime('%Y%m%d %H:%M:%S') == '20181003 09:19:00')

    assert r1.temp == 16.8
    assert r2.temp == 18.3
    assert r1.pressure == 1025.8
    assert r2.pressure == 1009.9


@pytest.fixture(autouse=True)
def prepare():
    testdata = Path(__file__).absolute().parent.parent / 'testdata'
    bmdata = testdata / 'hpi-testdata' / 'bluemaestro'
    assert bmdata.exists(), bmdata

    from my.cfg import config
    class user_config:
        export_path = bmdata
    config.bluemaestro = user_config # type: ignore
    yield
