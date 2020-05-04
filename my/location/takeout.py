"""
Location data from Google Takeout
"""

import json
from collections import deque
from datetime import datetime
from itertools import islice
from pathlib import Path
from typing import Any, Collection, Deque, Iterable, Iterator, List, NamedTuple, Optional, Sequence, IO
import pytz

# pip3 install geopy
import geopy # type: ignore
import geopy.distance # type: ignore

try:
    # pip3 install ijson cffi
    # cffi backend is almost 2x faster than default
    import ijson.backends.yajl2_cffi as ijson # type: ignore
except:
    # fallback to default backend. warning?
    import ijson # type: ignore

from ..common import get_files, LazyLogger, mcachew
from ..google.takeout.paths import get_last_takeout
from ..kython import kompress


logger = LazyLogger(__name__)


def cache_path(*args, **kwargs):
    from my.config import location as config
    return config.cache_path


Tag = Optional[str]

class Location(NamedTuple):
    dt: datetime
    lat: float
    lon: float
    alt: Optional[float]
    tag: Tag


# TODO use pool? not sure if that would really be faster...
def _iter_locations_fo(fo, start, stop) -> Iterator[Location]:
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


    for j in islice(ijson.items(fo, 'locations.item'), start, stop):
        dt = datetime.utcfromtimestamp(int(j["timestampMs"]) / 1000)
        if total % 10000 == 0:
            logger.info('processing item %d %s', total, dt)
        total += 1

        dt = pytz.utc.localize(dt)
        try:
            lat = float(j["latitudeE7"] / 10000000)
            lon = float(j["longitudeE7"] / 10000000)
            point = geopy.Point(lat, lon) # kinda sanity check that coordinates are ok
        except Exception as e:
            logger.exception(e)
            errors += 1
            if float(errors) / total > 0.01:
                raise RuntimeError('too many errors! aborting')
            else:
                continue

        alt = j.get("altitude", None)
        tag = tagger(dt, point) # TODO take accuracy into account??
        yield Location(
            dt=dt,
            lat=lat,
            lon=lon,
            alt=alt,
            tag=tag
        )


_LOCATION_JSON = 'Takeout/Location History/Location History.json'

# TODO hope they are sorted... (could assert for it)
@mcachew(cache_path, chunk_by=10000, logger=logger)
def _iter_locations(path: Path, start=0, stop=None) -> Iterator[Location]:
    ctx: IO[str]
    if path.suffix == '.json':
        ctx = path.open('r')
    else: # must be a takeout archive
        ctx = kompress.open(path, _LOCATION_JSON)

    with ctx as fo:
        yield from _iter_locations_fo(fo, start=start, stop=stop)
    # TODO wonder if old takeouts could contribute as well??


def iter_locations(**kwargs) -> Iterator[Location]:
    # TODO need to include older data
    last_takeout = get_last_takeout(path=_LOCATION_JSON)

    return _iter_locations(path=last_takeout, **kwargs)


def get_locations(*args, **kwargs) -> Sequence[Location]:
    return list(iter_locations(*args, **kwargs))


class LocInterval(NamedTuple):
    from_: Location
    to: Location


# TODO use this advanced iterators library?
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
