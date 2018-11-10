from typing import NamedTuple, Iterator, List, Iterable, Collection, Sequence
from datetime import datetime
from os import listdir
from os.path import join
from zipfile import ZipFile
import logging
import csv
import re
import json

import geopy.distance # type: ignore
# pip3 install ijson
import ijson # type: ignore

def get_logger():
    return logging.getLogger("location")

TAKEOUTS_PATH = "/path/to/takeout"
CACHE_PATH = "/L/data/.cache/location.pickle"

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
    last_takeout = max([f for f in listdir(TAKEOUTS_PATH) if re.match('takeout.*.zip', f)])
    jdata = None
    with ZipFile(join(TAKEOUTS_PATH, last_takeout)).open('Takeout/Location History/Location History.json') as fo:
        for j in ijson.items(fo, 'locations.item'):
            # TODO eh, not very streaming?..
            dt = datetime.fromtimestamp(int(j["timestampMs"]) / 1000) # TODO utc??
            lat = float(j["latitudeE7"] / 10000000)
            lon = float(j["longitudeE7"] / 10000000)
            tag = tagger(dt, lat, lon)
            yield Location(
                dt=dt,
                lat=lat,
                lon=lon,
                tag=tag
            )

def get_locations(cached: bool=False) -> Sequence[Location]:
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

# TOOD could cache groups too?... using 16% cpu is a bit annoying.. could also use some sliding window here
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
