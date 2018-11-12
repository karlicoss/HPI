from typing import NamedTuple, Iterator, List, Iterable, Collection, Sequence
from collections import deque
from itertools import islice
from datetime import datetime
import os
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
CACHE_PATH = "/L/data/.cache/location.picklel"

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
def load_locations() -> Iterator[Location]:
    last_takeout = max([f for f in listdir(TAKEOUTS_PATH) if re.match('takeout.*.zip', f)])
    jdata = None
    with ZipFile(join(TAKEOUTS_PATH, last_takeout)).open('Takeout/Location History/Location History.json') as fo:
        cc = 0
        for j in ijson.items(fo, 'locations.item'):
            dt = datetime.fromtimestamp(int(j["timestampMs"]) / 1000) # TODO utc??
            if cc % 10000 == 0:
                print(f'processing {dt}')
            cc += 1
            lat = float(j["latitudeE7"] / 10000000)
            lon = float(j["longitudeE7"] / 10000000)
            tag = tagger(dt, lat, lon)
            yield Location(
                dt=dt,
                lat=lat,
                lon=lon,
                tag=tag
            )

def iter_locations(cached: bool=False) -> Iterator[Location]:
    import dill # type: ignore
    if cached:
        with open(CACHE_PATH, 'rb') as fo:
            # TODO while fo has more data?
            while True:
                try:
                    pre = dill.load(fo)
                    yield Location(**pre._asdict())  # meh. but otherwise it's not serialising methods...
                except EOFError:
                    break
    else:
        yield from load_locations()


def get_locations(cached: bool=False) -> Sequence[Location]:
    return list(iter_locations(cached=cached))

class LocInterval(NamedTuple):
    from_: Location
    to: Location


# TODO kython? nicer interface?
class Window:
    def __init__(self, it):
        self.it = it
        self.storage = deque()
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

# TOOD could cache groups too?... using 16% cpu is a bit annoying.. could also use some sliding window here
# TODO maybe if tag is none, we just don't care?
def get_groups(cached: bool=False) -> List[LocInterval]:
    locsi = Window(iter_locations(cached=cached))
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
        # if i % 100 == 0:
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

# TODO ok, def cache groups.
def update_cache():
    import dill # type: ignore
    CACHE_PATH_TMP = CACHE_PATH + '.tmp'
    # TODO maybe, also keep on /tmp first?
    with open(CACHE_PATH_TMP, 'wb', 2 ** 20) as fo:
        for loc in iter_locations(cached=False):
            dill.dump(loc, fo)
    os.rename(CACHE_PATH_TMP, CACHE_PATH)
