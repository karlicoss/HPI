
# pip install geopy magic

from datetime import datetime
import itertools
import os
from os.path import join, basename
import json
import re
from typing import Tuple, Dict, Optional, NamedTuple, Iterator, Iterable, List

from geopy.geocoders import Nominatim # type: ignore

import magic # type: ignore

import PIL.Image # type: ignore
from PIL.ExifTags import TAGS, GPSTAGS # type: ignore

import logging
def get_logger():
    return logging.getLogger('photo-provider')

PATHS = [
    "***REMOVED***",
]

PHOTOS_URL = "***REMOVED***"


# TODO could use other pathes I suppose?
# TODO however then won't be accessible from dropbox

# PATH = "***REMOVED***/***REMOVED***"
# PATH = "***REMOVED***/***REMOVED***"

CACHE_PATH = "***REMOVED***"


# TODO hmm, instead geo could be a dynamic property... although a bit wasteful

# TODO insta photos should have instagram tag?

# TODO sokino -- wrong timestamp

_REGEXES = [re.compile(rs) for rs in [
    r'***REMOVED***',
    r'***REMOVED***',
    # TODO eh, some photos from ***REMOVED*** -- which is clearly bad datetime! like a default setting
    # TODO mm. maybe have expected datetime ranges for photos and discard everything else? some cameras looks like they god bad timestamps
]]

def ignore_path(p: str):
    for reg in _REGEXES:
        if reg.search(p):
            return True
    return False


_DT_REGEX = re.compile(r'\D(\d{8})\D*(\d{6})\D')
def dt_from_path(p: str) -> Optional[datetime]:
    name = basename(p)
    mm = _DT_REGEX.search(name)
    if mm is None:
        return None
    dates = mm.group(1) + mm.group(2)
    return datetime.strptime(dates, "%Y%m%d%H%M%S")

# TODO ignore hidden dirs?
LatLon = Tuple[float, float]

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
        for bp in PATHS:
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

def _try_photo(photo: str, mtype: str, dgeo: Optional[LatLon]) -> Optional[Photo]:
    logger = get_logger()

    geo: Optional[LatLon]

    dt: Optional[datetime] = None
    geo = dgeo
    if any(x in mtype for x in {'image/png', 'image/x-ms-bmp', 'video'}):
        logger.info(f"Skipping geo extraction for {photo} due to mime {mtype}")
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

# TODO ugh. need something like this, but tedious to reimplement..
# class Walker:
#     def __init__(self, root: str) -> None:
#         self.root = root

#     def walk(self):


#     def step(self, cur, dirs, files):
#         pass


# if geo information is missing from photo, you can specify it manually in geo.json file
def iter_photos() -> Iterator[Photo]:
    logger = get_logger()

    geolocator = Nominatim() # TODO does it cache??
    mime = magic.Magic(mime=True)

    for pp in PATHS:
        assert os.path.lexists(pp)

    geos: List[LatLon] = [] # stack of geos so we could use the most specific one
    # TODO could have this for all meta? e.g. time
    for d, _, files in itertools.chain.from_iterable((os.walk(pp, followlinks=True) for pp in PATHS)):
        logger.info(f"Processing {d}")

        geof = join(d, 'geo.json')
        cgeo = None
        if os.path.isfile(geof):
            j: Dict
            with open(geof, 'r') as fo:
                j = json.load(fo)
            if 'name' in j:
                g = geolocator.geocode(j['name'])
                geo = (g.latitude, g.longitude)
            else:
                geo = j['lat'], j['lon']
            geos.append(geo)

        for f in sorted(files):
            photo = join(d, f)
            if ignore_path(photo):
                logger.info(f"Ignoring {photo} due to regex")
                continue

            mtype = mime.from_file(photo)

            IGNORED = {
                'application',
                'audio',
                'text',
                'inode',
            }
            if any(i in mtype for i in IGNORED):
                logger.info(f"Ignoring {photo} due to mime {mtype}")
                continue

            try:
                dgeo = None if len(geos) == 0 else geos[-1]
                p = _try_photo(photo, mtype, dgeo)
                if p is not None:
                    yield p
            except Exception as e:
                raise RuntimeError(f'Error while processing {photo}') from e

        if cgeo is not None:
            geos.pop()

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
