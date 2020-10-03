#!/usr/bin/env python3
from pathlib import Path

from my.core.cachew import disable_cachew
disable_cachew()  # meh


def test() -> None:
    from my.bluemaestro import measurements
    res = list(measurements())
    assert len(res) > 1000


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
