from typing import NamedTuple, Iterator, List, Iterable
from datetime import datetime
import logging
import csv
import geopy.distance # type: ignore

def get_logger():
    return logging.getLogger("location")

PATH = "/L/data/location/location.csv"
CACHE_PATH = "/L/.cache/location.cache"

# TODO need to cache?
# TODO tag??

Tag = str

class Location(NamedTuple):
    dt: datetime
    lat: float
    lon: float
    tag: Tag


def tagger(dt: datetime, lat: float, lon: float) -> Tag:
    TAGS = [
 # removed
    ]
    for coord, dist, tag in TAGS:
        if geopy.distance.distance(coord, (lat, lon)).m  < dist:
            return tag
    else:
        return "other"

# TODO hope they are sorted...
# TODO that could also serve as basis for timezone provider.
def iter_locations() -> Iterator[Location]:
    with open(PATH) as fo:
        reader = csv.reader(fo)
        next(reader) # skip header
        for ll in reader:
            [ts, lats, lons] = ll
            # TODO hmm, is it local??
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            lat = float(lats)
            lon = float(lons)
            tag = tagger(dt, lat, lon)
            yield Location(
                dt=dt,
                lat=lat,
                lon=lon,
                tag=tag
            )

def get_locations(cached: bool=False) -> Iterable[Location]:
    import dill # type: ignore
    if cached:
        with open(CACHE_PATH, 'rb') as fo:
            preph = dill.load(fo)
            return [Location(**p._asdict()) for p in preph] # meh. but otherwise it's not serialising methods...
    else:
        return list(iter_locations())

class LocInterval(NamedTuple):
    from_: Location
    to: Location

def get_groups(cached: bool=False) -> List[LocInterval]:
    locs = get_locations(cached=cached)
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
            groups.append(LocInterval(from_=curg[0], to=curg[-1]))
            curg = []

    while i < len(locs):
        last = None if len(curg) == 0 else curg[-1]
        cur = locs[i]
        j = i
        match = False
        while not match and j < len(locs) and j < i + 10: # TODO FIXME time distance here... e.g. half an hour?
            cur = locs[j]
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
    import dill # type: ignore
    datas = get_locations(cached=False)
    with open(CACHE_PATH, 'wb') as fo:
        dill.dump(datas, fo)
