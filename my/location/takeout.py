"""
Location data from Google Takeout
"""

import json
from collections import deque
from datetime import datetime
from itertools import islice
from pathlib import Path
from typing import Any, Collection, Deque, Iterable, Iterator, List, NamedTuple, Optional, Sequence, IO, Tuple
import re

import pytz

# pip3 install geopy
import geopy # type: ignore
import geopy.distance # type: ignore

from ..core.common import get_files, LazyLogger, mcachew
from ..core.cachew import cache_dir
from ..google.takeout.paths import get_last_takeout
from ..kython import kompress


logger = LazyLogger(__name__)


Tag = Optional[str]

# todo maybe don't tag by default?
class Location(NamedTuple):
    dt: datetime
    lat: float
    lon: float
    alt: Optional[float]
    tag: Tag


TsLatLon = Tuple[int, int, int]


def _iter_via_ijson(fo) -> Iterator[TsLatLon]:
    # ijson version takes 25 seconds for 1M items (without processing)
    try:
        # pip3 install ijson cffi
        import ijson.backends.yajl2_cffi as ijson # type: ignore
    except:
        import warnings
        warnings.warn("Falling back to default ijson because 'cffi' backend isn't found. It's up to 2x faster, you might want to check it out")
        import ijson # type: ignore

    for d in ijson.items(fo, 'locations.item'):
        yield (
            int(d['timestampMs']),
            d['latitudeE7' ],
            d['longitudeE7'],
        )


def _iter_via_grep(fo) -> Iterator[TsLatLon]:
    # grep version takes 5 seconds for 1M items (without processing)
    x = [None, None, None]
    for i, line in enumerate(fo):
        if i > 0 and i % 3 == 0:
            yield tuple(x)
        n = re.search(b': "?(-?\\d+)"?,?$', line) # meh. somewhat fragile...
        j = i % 3
        x[j] = int(n.group(1).decode('ascii'))
    # make sure it's read what we expected
    assert (i + 1) % 3 == 0
    yield tuple(x)


# todo could also use pool? not sure if that would really be faster...
# earch thread could process 100K at once?
# would need to find out a way to know when to stop? process in some sort of sqrt progression??


def _iter_locations_fo(fit) -> Iterator[Location]:
    total = 0
    errors = 0

    try:
        from my.config.locations import LOCATIONS as known_locations
    except ModuleNotFoundError as e:
        name = 'my.config.locations'
        if e.name != name:
            raise e
        logger.warning("'%s' isn't found. setting known_locations to empty list", name)
        known_locations = []

    # TODO tagging should be takeout-agnostic
    def tagger(dt: datetime, point: geopy.Point) -> Tag:
        '''
        Tag points with known locations (e.g. work/home/etc)
        '''
        for lat, lon, dist, tag in known_locations:
            # TODO use something more efficient?
            if geopy.distance.distance((lat, lon), point).m  < dist:
                return tag
        else:
            return None

    for tsMs, latE7, lonE7 in fit:
        dt = datetime.fromtimestamp(tsMs / 1000, tz=pytz.utc)
        total += 1
        if total % 10000 == 0:
            logger.info('processing item %d %s', total, dt)

        try:
            lat = float(latE7 / 1e7)
            lon = float(lonE7 / 1e7)
            # note: geopy is quite slow..
            point = geopy.Point(lat, lon) # kinda sanity check that coordinates are ok
        except Exception as e:
            logger.exception(e)
            errors += 1
            if float(errors) / total > 0.01:
                raise RuntimeError('too many errors! aborting')
            else:
                continue

        # todo support later
        # alt = j.get("altitude", None)
        alt = None
        # todo enable tags later
        # tag = tagger(dt, point) # TODO take accuracy into account??
        tag = None
        yield Location(
            dt=dt,
            lat=lat,
            lon=lon,
            alt=alt,
            tag=tag
        )


_LOCATION_JSON = 'Takeout/Location History/Location History.json'

# todo if start != 0, disable cache? again this is where nicer caching would come handy
# TODO hope they are sorted... (could assert for it)
@mcachew(cache_dir() / 'google_location.cache', logger=logger)
def _iter_locations(path: Path, start=0, stop=None) -> Iterator[Location]:
    ctx: IO[str]
    if path.suffix == '.json':
        # todo: to support, should perhaps provide it as input= to Popen
        raise RuntimeError("Temporary not supported")
        ctx = path.open('r')
    else: # must be a takeout archive
        # todo CPath? although not sure if it can be iterative?
        ctx = kompress.open(path, _LOCATION_JSON)

    # with ctx as fo:
    #     fit = _iter_via_ijson(fo)
    #     fit = islice(fit, start, stop)
    #     yield from _iter_locations_fo(fit)
  
    unzip = f'unzip -p "{path}" "{_LOCATION_JSON}"'
    extract = "grep -E '^    .(timestampMs|latitudeE7|longitudeE7)'"
    from subprocess import Popen, PIPE
    with Popen(f'{unzip} | {extract}', shell=True, stdout=PIPE) as p:
        out = p.stdout; assert out is not None
        fit = _iter_via_grep(out)
        fit = islice(fit, start, stop)
        yield from _iter_locations_fo(fit)
    # todo wonder if old takeouts could contribute as well??


def iter_locations(**kwargs) -> Iterator[Location]:
    # TODO need to include older data
    last_takeout = get_last_takeout(path=_LOCATION_JSON)

    return _iter_locations(path=last_takeout, **kwargs)


def get_locations(*args, **kwargs) -> Sequence[Location]:
    return list(iter_locations(*args, **kwargs))


class LocInterval(NamedTuple):
    from_: Location
    to: Location


# TODO use more_itertools
# TODO kython? nicer interface?
class Window:
    def __init__(self, it):
        self.it = it
        self.storage: Deque[Any] = deque()
        self.start = 0
        self.end = 0

    # TODO need check for existence?
    def load_to(self, to):
        while to >= self.end:
            try:
                ii = next(self.it)
                self.storage.append(ii)
                self.end += 1
            except StopIteration:
                break
    def exists(self, i):
        self.load_to(i)
        return i < self.end

    def consume_to(self, i):
        self.load_to(i)
        consumed = i - self.start
        self.start = i
        for _ in range(consumed):
            self.storage.popleft()

    def __getitem__(self, i):
        self.load_to(i)
        ii = i - self.start
        assert ii >= 0
        return self.storage[ii]



# TODO cachew as well?
# TODO maybe if tag is none, we just don't care?
def get_groups(*args, **kwargs) -> List[LocInterval]:
    all_locations = iter(iter_locations(*args, **kwargs))
    locsi = Window(all_locations)
    i = 0
    groups: List[LocInterval] = []
    curg: List[Location] = []

    def add_to_group(x):
        nonlocal curg
        if len(curg) < 2:
            curg.append(x)
        else:
            curg[-1] = x

    def dump_group():
        nonlocal curg
        if len(curg) > 0:
            # print("new group")
            groups.append(LocInterval(from_=curg[0], to=curg[-1]))
            curg = []

    while locsi.exists(i):
        if i % 10000 == 0:
            logger.debug('grouping item %d', i)

        locsi.consume_to(i)

        last = None if len(curg) == 0 else curg[-1]
        cur = locsi[i]
        j = i
        match = False
        while not match and locsi.exists(j) and j < i + 10: # TODO FIXME time distance here... e.g. half an hour?
            cur = locsi[j]
            if last is None or cur.tag == last.tag:
                # ok
                add_to_group(cur)
                i = j + 1
                match = True
            else:
                j += 1
        # if we made here without advancing
        if not match:
            dump_group()
            i += 1
        else:
            pass
    dump_group()
    return groups


# TODO not sure if necessary anymore...
def update_cache():
    # TODO perhaps set hash to null instead, that's a bit less intrusive
    cp = cache_path()
    if cp.exists():
        cp.unlink()
    for _ in iter_locations():
        pass
