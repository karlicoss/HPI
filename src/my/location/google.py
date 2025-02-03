"""
Location data from Google Takeout

DEPRECATED: setup my.google.takeout.parser and use my.location.google_takeout instead
"""
from __future__ import annotations

REQUIRES = [
    'geopy', # checking that coordinates are valid
    'ijson',
]

import re
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from subprocess import PIPE, Popen
from typing import IO, NamedTuple, Optional

import geopy  # type: ignore[import-not-found]

from my.core import Stats, make_logger, stat, warnings
from my.core.cachew import cache_dir, mcachew

warnings.high("Please set up my.google.takeout.parser module for better takeout support")


 # otherwise uses ijson
 # todo move to config??
USE_GREP = False


logger = make_logger(__name__)


class Location(NamedTuple):
    dt: datetime
    lat: float
    lon: float
    alt: Optional[float]


TsLatLon = tuple[int, int, int]


def _iter_via_ijson(fo) -> Iterable[TsLatLon]:
    # ijson version takes 25 seconds for 1M items (without processing)
    # todo extract to common?
    try:
        # pip3 install ijson cffi
        import ijson.backends.yajl2_cffi as ijson  # type: ignore[import-untyped]
    except:
        warnings.medium("Falling back to default ijson because 'cffi' backend isn't found. It's up to 2x faster, you might want to check it out")
        import ijson  # type: ignore[import-untyped]

    for d in ijson.items(fo, 'locations.item'):
        yield (
            int(d['timestampMs']),
            d['latitudeE7' ],
            d['longitudeE7'],
        )


# todo ugh. fragile, not sure, maybe should do some assert in advance?
def _iter_via_grep(fo) -> Iterable[TsLatLon]:
    # grep version takes 5 seconds for 1M items (without processing)
    x = [-1, -1, -1]
    for i, line in enumerate(fo):
        if i > 0 and i % 3 == 0:
            yield tuple(x) # type: ignore[misc]
        n = re.search(b': "?(-?\\d+)"?,?$', line) # meh. somewhat fragile...
        assert n is not None
        j = i % 3
        x[j] = int(n.group(1).decode('ascii'))
    # make sure it's read what we expected
    assert (i + 1) % 3 == 0
    yield tuple(x) # type: ignore[misc]


# todo could also use pool? not sure if that would really be faster...
# search thread could process 100K at once?
# would need to find out a way to know when to stop? process in some sort of sqrt progression??


def _iter_locations_fo(fit) -> Iterable[Location]:
    total = 0
    errors = 0

    for tsMs, latE7, lonE7 in fit:
        dt = datetime.fromtimestamp(tsMs / 1000, tz=timezone.utc)
        total += 1
        if total % 10000 == 0:
            logger.info('processing item %d %s', total, dt)

        try:
            lat = float(latE7 / 1e7)
            lon = float(lonE7 / 1e7)
            # note: geopy is quite slow..
            _point = geopy.Point(lat, lon) # kinda sanity check that coordinates are ok
        except Exception as e:
            logger.exception(e)
            errors += 1
            if float(errors) / total > 0.01:
                # todo make defensive?
                # todo exceptiongroup?
                raise RuntimeError('too many errors! aborting')  # noqa: B904
            else:
                continue

        # todo support later
        # alt = j.get("altitude", None)
        alt = None
        yield Location(
            dt=dt,
            lat=lat,
            lon=lon,
            alt=alt,
        )


_LOCATION_JSON = 'Takeout/Location History/Location History.json'

# todo if start != 0, disable cache? again this is where nicer caching would come handy
# TODO hope they are sorted... (could assert for it)
# todo configure cache automatically?
@mcachew(cache_dir(), logger=logger)
def _iter_locations(path: Path, start=0, stop=None) -> Iterable[Location]:
    ctx: IO[str]
    if path.suffix == '.json':
        # todo: to support, should perhaps provide it as input= to Popen
        raise RuntimeError("Temporary not supported")
        ctx = path.open('r')
    else: # must be a takeout archive
        # todo CPath? although not sure if it can be iterative?
        ctx = (path / _LOCATION_JSON).open()

    if USE_GREP:
        unzip = f'unzip -p "{path}" "{_LOCATION_JSON}"'
        extract = "grep -E '^    .(timestampMs|latitudeE7|longitudeE7)'"
        with Popen(f'{unzip} | {extract}', shell=True, stdout=PIPE) as p:
            out = p.stdout; assert out is not None
            fit = _iter_via_grep(out)
            fit = islice(fit, start, stop)
            yield from _iter_locations_fo(fit)
    else:
        with ctx as fo:
            # todo need to open as bytes
            fit = _iter_via_ijson(fo)
            fit = islice(fit, start, stop)
            yield from _iter_locations_fo(fit)
    # todo wonder if old takeouts could contribute as well??


def locations(**kwargs) -> Iterable[Location]:
    # NOTE: if this import isn't lazy, tests/tz.py breaks because it can't override config
    # very weird, as if this function captures the values of globals somehow?? investigate later.
    from ..google.takeout.paths import get_last_takeout
    last_takeout = get_last_takeout(path=_LOCATION_JSON)
    if last_takeout is None:
        return []

    return _iter_locations(path=last_takeout, **kwargs)


def stats() -> Stats:
    return stat(locations)


# todo add dataframe

# todo deprecate?
def get_locations(*args, **kwargs) -> Sequence[Location]:
    return list(locations(*args, **kwargs))
