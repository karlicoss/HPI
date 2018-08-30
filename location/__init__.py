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

def update_cache():
    import dill # type: ignore
    datas = get_locations(cached=False)
    with open(CACHE_PATH, 'wb') as fo:
        dill.dump(datas, fo)
