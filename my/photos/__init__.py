"""
Module for accessing photos and videos on the filesystem
"""

# pip install geopy magic

from datetime import datetime
import json
from pathlib import Path
from typing import Tuple, Dict, Optional, NamedTuple, Iterator, Iterable, List

from geopy.geocoders import Nominatim # type: ignore
import magic # type: ignore

from ..common import LazyLogger, mcachew

from mycfg import photos as config


logger = LazyLogger('my.photos')
log = logger



# TODO ignore hidden dirs?
class LatLon(NamedTuple):
    lat: float
    lon: float

# TODO PIL.ExifTags.TAGS


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


from .utils import get_exif_from_file, ExifTags, Exif, dt_from_path, convert_ref

def _try_photo(photo: Path, mtype: str, *, parent_geo: Optional[LatLon]) -> Photo:
    exif: Exif
    if any(x in mtype for x in {'image/png', 'image/x-ms-bmp', 'video'}):
        # TODO don't remember why..
        log.debug(f"skipping exif extraction for {photo} due to mime {mtype}")
        exif = {}
    else:
        exif = get_exif_from_file(photo)

    def _get_geo() -> Optional[LatLon]:
        meta = exif.get(ExifTags.GPSINFO, {})
        if ExifTags.LAT in meta and ExifTags.LON in meta:
            return LatLon(
                lat=convert_ref(meta[ExifTags.LAT], meta[ExifTags.LAT_REF]),
                lon=convert_ref(meta[ExifTags.LON], meta[ExifTags.LON_REF]),
            )
        return parent_geo

    # TODO aware on unaware?
    def _get_dt() -> Optional[datetime]:
        edt = exif.get(ExifTags.DATETIME, None)
        if edt is not None:
            dtimes = edt.replace(' 24', ' 00')  # jeez maybe log it?
            if dtimes == "0000:00:00 00:00:00":
                log.warning(f"Bad exif timestamp {dtimes} for {photo}")
            else:
                dt = datetime.strptime(dtimes, '%Y:%m:%d %H:%M:%S')
                # TODO timezone is local, should take into account...
                return dt

        if 'Instagram/VID_' in str(photo):
            # TODO bit random...
            log.warning('ignoring timestamp extraction for %s, they are stupid for Instagram videos', photo)
            return None

        # TODO FIXME result type here??
        edt = dt_from_path(photo)  # ok, last try..

        if edt is None:
            return None

        if edt is not None and edt > datetime.now():
            # TODO also yield?
            logger.error('datetime for %s is too far in future: %s', photo, edt)
            return None

        return edt

    geo = _get_geo()
    dt  = _get_dt()

    return Photo(str(photo), dt=dt, geo=geo)


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
# TODO is there something more standard?
# @mcachew(cache_path=config.cache_path)
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

        parent_geo = get_geo(path.parent)
        mime = fastermime(str(path))
        p = _try_photo(path, mime, parent_geo=parent_geo)
        yield p


def print_all():
    for p in photos():
        print(f"{p.dt} {p.path} {p.tags}")

# TODO cachew -- improve AttributeError: type object 'tuple' has no attribute '__annotations__' -- improve errors?
# TODO cachew -- invalidate if function code changed?
