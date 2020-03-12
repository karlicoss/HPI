
# pip install geopy magic

from datetime import datetime
import itertools
import os
from os.path import join, basename
import json
import re
from pathlib import Path
from typing import Tuple, Dict, Optional, NamedTuple, Iterator, Iterable, List

from geopy.geocoders import Nominatim # type: ignore

import magic # type: ignore

import PIL.Image # type: ignore
from PIL.ExifTags import TAGS, GPSTAGS # type: ignore


from ..common import LazyLogger, mcachew


logger = LazyLogger('my.photos')
log = logger


from mycfg import photos as config



_DT_REGEX = re.compile(r'\D(\d{8})\D*(\d{6})\D')
def dt_from_path(p: str) -> Optional[datetime]:
    name = basename(p)
    mm = _DT_REGEX.search(name)
    if mm is None:
        return None
    dates = mm.group(1) + mm.group(2)
    return datetime.strptime(dates, "%Y%m%d%H%M%S")

# TODO ignore hidden dirs?
class LatLon(NamedTuple):
    lat: float
    lon: float

# TODO PIL.ExifTags.TAGS

DATETIME = "DateTimeOriginal"
LAT      = "GPSLatitude"
LAT_REF  = "GPSLatitudeRef"
LON     = "GPSLongitude"
LON_REF = "GPSLongitudeRef"
GPSINFO = "GPSInfo"

# TODO kython??
def get_exif_data(image):
    """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == GPSINFO:
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]

                exif_data[decoded] = gps_data
            else:
                exif_data[decoded] = value

    return exif_data

def to_degree(value):
    """Helper function to convert the GPS coordinates
    stored in the EXIF to degress in float format"""
    d0 = value[0][0]
    d1 = value[0][1]
    d = float(d0) / float(d1)
    m0 = value[1][0]
    m1 = value[1][1]
    m = float(m0) / float(m1)

    s0 = value[2][0]
    s1 = value[2][1]
    s = float(s0) / float(s1)

    return d + (m / 60.0) + (s / 3600.0)

def convert(cstr, ref: str):
    val = to_degree(cstr)
    if ref == 'S' or ref == 'W':
        val = -val
    return val


class Photo(NamedTuple):
    path: str
    dt: Optional[datetime]
    geo: Optional[LatLon]
    # TODO can we always extract date? I guess not...

    @property
    def tags(self) -> List[str]: # TODO
        return []

    @property
    def _basename(self) -> str:
        for bp in config.paths:
            if self.path.startswith(bp):
                return self.path[len(bp):]
        else:
            raise RuntimeError(f'Weird path {self.path}, cant match against anything')

    @property
    def linkname(self) -> str:
        return self._basename.strip('/')

    @property
    def url(self) -> str:
        return PHOTOS_URL + self._basename


def _try_photo(photo: str, mtype: str, dgeo: Optional[LatLon]) -> Photo:
    geo: Optional[LatLon]

    dt: Optional[datetime] = None
    geo = dgeo
    if any(x in mtype for x in {'image/png', 'image/x-ms-bmp', 'video'}):
        log.debug(f"skipping geo extraction for {photo} due to mime {mtype}")
    else:
        edata: Dict
        try:
            with PIL.Image.open(photo) as fo:
                edata = get_exif_data(fo)
        except Exception as e:
            logger.warning(f"Couln't get exif for {photo}") # TODO meh
            logger.exception(e)
        else:
            dtimes = edata.get('DateTimeOriginal', None)
            if dtimes is not None:
                try:
                    dtimes = dtimes.replace(' 24', ' 00') # jeez maybe log it?
                    if dtimes == "0000:00:00 00:00:00":
                        logger.info(f"Bad exif timestamp {dtimes} for {photo}")
                    else:
                        dt = datetime.strptime(dtimes, '%Y:%m:%d %H:%M:%S')
                # # TODO timezone is local, should take into account...
                except Exception as e:
                    logger.error(f"Error while trying to extract date from EXIF {photo}")
                    logger.exception(e)

            meta = edata.get(GPSINFO, {})
            if LAT in meta and LON in meta:
                lat = convert(meta[LAT], meta[LAT_REF])
                lon = convert(meta[LON], meta[LON_REF])
                geo = (lat, lon)
    if dt is None:
        if 'Instagram/VID_' in photo:
            logger.warning('ignoring timestamp extraction for %s, they are stupid for Instagram videos', photo)
        else:
            try:
                edt = dt_from_path(photo) # ok, last try..
            except Exception as e:
                # TODO result type?
                logger.error(f"Error while trying to extract date from name {photo}")
                logger.exception(e)
            else:
                if edt is not None and edt > datetime.now():
                    logger.error('datetime for %s is too far in future: %s', photo, edt)
                else:
                    dt = edt


    return Photo(photo, dt, geo)
    # plink = f"file://{photo}"
    # plink = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Ichthyornis_Clean.png/800px-Ichthyornis_Clean.png"
    # yield (geo, src.color, plink)


import mimetypes # TODO do I need init()?
def fastermime(path: str, mgc=magic.Magic(mime=True)) -> str:
    # mimetypes is faster
    (mime, _) = mimetypes.guess_type(path)
    if mime is not None:
        return mime
    # magic is slower but returns more stuff
    # TODO FIXME Result type; it's inherently racey
    return mgc.from_file(path)


# TODO exclude
def _candidates() -> Iterable[str]:
    # TODO that could be a bit slow if there are to many extra files?
    from subprocess import Popen, PIPE
    with Popen([
            'fdfind',
            '--follow',
            '-t', 'file',
            '.',
            *config.paths,
    ], stdout=PIPE) as p:
        for line in p.stdout:
            path = line.decode('utf8').rstrip('\n')
            mime = fastermime(path)
            tp = mime.split('/')[0]
            if tp in {'inode', 'text', 'application', 'audio'}:
                continue
            if tp not in {'image', 'video'}:
                # TODO yield error?
                logger.warning('%s: unexpected mime %s', path, tp)
            # TODO return mime too? so we don't have to call it again in _photos?
            yield path


def photos() -> Iterator[Photo]:
    candidates = tuple(sorted(_candidates()))
    return _photos(candidates)
    # TODO figure out how to use cachew without helper function?
    # I guess need lazy variables or something?


# if geo information is missing from photo, you can specify it manually in geo.json file
# @mcachew(logger=logger)
def _photos(candidates: Iterable[str]) -> Iterator[Photo]:
    geolocator = Nominatim() # TODO does it cache??

    from functools import lru_cache
    @lru_cache(None)
    def get_geo(d: Path) -> Optional[LatLon]:
        geof = d / 'geo.json'
        if not geof.exists():
            if d == d.parent:
                return None
            else:
                return get_geo(d.parent)

        j = json.loads(geof.read_text())
        if 'name' in j:
            g = geolocator.geocode(j['name'])
            lat = g.latitude
            lon = g.longitude
        else:
            lat = j['lat']
            lon = j['lon']
        return LatLon(lat=lat, lon=lon)


    for path in map(Path, candidates):
        if config.ignored(path):
            log.info('ignoring %s due to config', path)
            continue

        geo = get_geo(path.parent)
        mime = fastermime(str(path))
        p = _try_photo(str(path), mime, geo)
        yield p



def get_photos(cached: bool=False) -> List[Photo]:
    # TODO get rid of it, use cachew..
    import dill # type: ignore
    if cached:
        with open(CACHE_PATH, 'rb') as fo:
            preph = dill.load(fo)
            return [Photo(**p._asdict()) for p in preph] # meh. but otherwise it's not serialising methods...
    else:
        return list(iter_photos())

# TODO python3 -m photos update_cache
def update_cache():
    import dill # type: ignore
    photos = get_photos(cached=False)
    with open(CACHE_PATH, 'wb') as fo:
        dill.dump(photos, fo)

# TODO cachew -- improve AttributeError: type object 'tuple' has no attribute '__annotations__' -- improve errors?
# TODO cachew -- invalidate if function code changed?
