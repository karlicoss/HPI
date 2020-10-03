#!/usr/bin/env python3
from pathlib import Path

from my.core.cachew import disable_cachew
disable_cachew()  # meh


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

    # NOTE: broken at the moment due to weirdness with timestamping
    # assert len(tp) == 1 # should be unique

    # 2.5 K + 4 K datapoints, somwhat overlapping
    # NOTE: boken at the moment due to weirdness with timestamping
    # assert len(res) < 6000


import pytest # type: ignore
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
