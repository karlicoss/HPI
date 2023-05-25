# Defines some shared config for tests

from datetime import datetime, date, timezone
from pathlib import Path

from typing import Any, NamedTuple
import my.time.tz.via_location as LTZ
from more_itertools import one


class SharedConfig(NamedTuple):
    google: Any
    location: Any
    time: Any


def _prepare_google_config(tmp_path: Path):
    from my.tests.common import testdata
    try:
        track = one(testdata().rglob('italy-slovenia-2017-07-29.json'))
    except ValueError:
        raise RuntimeError('testdata not found, setup git submodules?')


    # todo ugh. unnecessary zipping, but at the moment takeout provider doesn't support plain dirs
    import zipfile
    with zipfile.ZipFile(tmp_path / 'takeout.zip', 'w') as zf:
        zf.writestr('Takeout/Location History/Location History.json', track.read_bytes())

    class google_config:
        takeout_path = tmp_path
    return google_config


# pass tmp_path from pytest to this helper function
# see tests/tz.py as an example
def temp_config(temp_path: Path) -> Any:
    from my.tests.common import reset_modules
    reset_modules()

    LTZ.config.fast = True

    class location:
        home_accuracy = 30_000
        home = (
            # supports ISO strings
            ('2005-12-04'                                       , (42.697842, 23.325973)), # Bulgaria, Sofia
            # supports date/datetime objects
            (date(year=1980, month=2, day=15)                   , (40.7128  , -74.0060 )), # NY
            # check tz handling..
            (datetime.fromtimestamp(1600000000, tz=timezone.utc), (55.7558  , 37.6173  )), # Moscow, Russia
        )
        # note: order doesn't matter, will be sorted in the data provider
        class via_ip:
            accuracy = 15_000
        class gpslogger:
            pass

    class time:
        class tz:
            class via_location:
                pass # just rely on the defaults...


    return SharedConfig(google=_prepare_google_config(temp_path), location=location, time=time)
