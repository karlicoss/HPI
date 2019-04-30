from typing import NamedTuple, Iterator, List, Iterable, Collection, Sequence, Deque, Any, Optional
from collections import deque
from itertools import islice
from datetime import datetime
from zipfile import ZipFile
import logging
import csv
import re
import json
from pathlib import Path
import pytz


from kython import kompress
from kython.kcache import make_dbcache, mtime_hash


# pipe install geopy
import geopy # type: ignore
import geopy.distance # type: ignore
# pip3 install ijson
import ijson # type: ignore

def get_logger():
    return logging.getLogger("location")


TAKEOUTS_PATH = Path("/path/to/takeout")


Tag = str

class Location(NamedTuple):
    dt: datetime
    lat: float
    lon: float
    alt: Optional[float]
    tag: Tag

dbcache = make_dbcache('/L/data/.cache/location.sqlite', hashf=mtime_hash, type_=Location)


def tagger(dt: datetime, point: geopy.Point) -> Tag:
    TAGS = [
 # removed
    ]
    for coord, dist, tag in TAGS:
        if geopy.distance.distance(coord, point).m  < dist:
            return tag
    else:
        return "other"


# TODO careful, might not fit in glumov ram...
def _iter_locations_fo(fo) -> Iterator[Location]:
    logger = get_logger()
    total = 0
    errors = 0

    for j in ijson.items(fo, 'locations.item'):
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

# TODO hope they are sorted...
# TODO that could also serve as basis for tz provider
@dbcache
def _iter_locations(path: Path) -> List[Location]:
    limit = None
    # TODO FIXME support archives
    with path.open('r') as fo:
        return list(islice(_iter_locations_fo(fo), 0, limit))

    # TODO wonder if old takeouts could contribute as well??
    # with kompress.open(last_takeout, 'Takeout/Location History/Location History.json') as fo:
    #     return _iter_locations_fo(fo)


# TODO shit.. should support iterator..
def iter_locations() -> List[Location]:
    last_takeout = max(TAKEOUTS_PATH.glob('takeout*.zip'))
    last_takeout = Path('/L/tmp/LocationHistory.json')
    return _iter_locations(last_takeout)

    import sys
    sys.path.append('/L/Dropbox/data/location_provider') # jeez.. otherwise it refuses to unpickle :(


def get_locations(cached: bool=False) -> Sequence[Location]:
    return list(iter_locations(cached=cached))

class LocInterval(NamedTuple):
    from_: Location
    to: Location


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



# TODO maybe if tag is none, we just don't care?
def get_groups() -> List[LocInterval]:
    all_locations = iter(iter_locations()) # TODO 
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
        # if i % 1000 == 0:
        #     print("processing " + str(i))
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

def update_cache():
    import pickle as dill # type: ignore
    CACHE_PATH_TMP = CACHE_PATH.with_suffix('.tmp')
    # TODO maybe, also keep on /tmp first?

    with CACHE_PATH_TMP.open('wb', 2 ** 20) as fo:
        for loc in iter_locations(cached=False):
            dill.dump(loc, fo)
    CACHE_PATH_TMP.rename(CACHE_PATH)
