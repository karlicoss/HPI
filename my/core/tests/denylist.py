import json
import warnings
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from ..denylist import DenyList


class IP(NamedTuple):
    addr: str
    dt: datetime


def data() -> Iterator[IP]:
    # random IP addresses
    yield IP(addr="67.98.113.0", dt=datetime(2020, 1, 1))
    yield IP(addr="59.40.113.87", dt=datetime(2020, 2, 1))
    yield IP(addr="161.235.192.228", dt=datetime(2020, 3, 1))
    yield IP(addr="165.243.139.87", dt=datetime(2020, 4, 1))
    yield IP(addr="69.69.141.154", dt=datetime(2020, 5, 1))
    yield IP(addr="50.72.224.80", dt=datetime(2020, 6, 1))
    yield IP(addr="221.67.89.168", dt=datetime(2020, 7, 1))
    yield IP(addr="177.113.119.251", dt=datetime(2020, 8, 1))
    yield IP(addr="93.200.246.215", dt=datetime(2020, 9, 1))
    yield IP(addr="127.105.171.61", dt=datetime(2020, 10, 1))


def test_denylist(tmp_path: Path) -> None:
    tf = (tmp_path / "denylist.json").absolute()
    with warnings.catch_warnings(record=True):
        # create empty denylist (though file does not have to exist for denylist to work)
        tf.write_text("[]")

        d = DenyList(tf)

        d.load()
        assert dict(d._deny_map) == {}
        assert d._deny_raw_list == []

        assert list(d.filter(data())) == list(data())
        # no data in denylist yet
        assert len(d._deny_map) == 0
        assert len(d._deny_raw_list) == 0

        # add some data
        d.deny(key="addr", value="67.98.113.0")
        # write and reload to update _deny_map, _deny_raw_list
        d.write()
        d.load()

        assert len(d._deny_map) == 1
        assert len(d._deny_raw_list) == 1

        assert d._deny_raw_list == [{"addr": "67.98.113.0"}]

        filtered = list(d.filter(data()))
        assert len(filtered) == 9
        assert "67.98.113.0" not in [i.addr for i in filtered]

        assert dict(d._deny_map) == {"addr": {"67.98.113.0"}}

        denied = list(d.filter(data(), invert=True))
        assert len(denied) == 1

        assert denied[0] == IP(addr="67.98.113.0", dt=datetime(2020, 1, 1))

        # add some non-JSON primitive data

        d.deny(key="dt", value=datetime(2020, 2, 1))

        # test internal behavior, _deny_raw_list should have been updated,
        # but _deny_map doesn't get updated by a call to .deny
        #
        # if we change this just update the test, is just here to ensure
        # this is the behaviour

        assert len(d._deny_map) == 1

        # write and load to update _deny_map
        d.write()
        d.load()

        assert len(d._deny_map) == 2
        assert len(d._deny_raw_list) == 2

        assert d._deny_raw_list[-1] == {"dt": "2020-02-01T00:00:00"}

        filtered = list(d.filter(data()))
        assert len(filtered) == 8

        assert "59.40.113.87" not in [i.addr for i in filtered]

        data_json = json.loads(tf.read_text())

        assert data_json == [
            {
                "addr": "67.98.113.0",
            },
            {
                "dt": "2020-02-01T00:00:00",
            },
        ]
