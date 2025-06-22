"""
Photos and videos on your filesystem, their GPS and timestamps
"""

from __future__ import annotations

REQUIRES = [
    'geopy',
    'magic',
]
# NOTE: also uses fdfind to search photos

import json
from collections.abc import Iterable, Iterator
from concurrent.futures import ProcessPoolExecutor as Pool
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional

from geopy.geocoders import Nominatim  # type: ignore[import-not-found]

from my.core import LazyLogger
from my.core.cachew import cache_dir, mcachew
from my.core.error import Res, sort_res_by
from my.core.mime import fastermime

from my.config import photos as config  # type: ignore[attr-defined]  # isort: skip

logger = LazyLogger(__name__)


# TODO ignore hidden dirs?
class LatLon(NamedTuple):
    lat: float
    lon: float


class Photo(NamedTuple):
    path: str
    dt: Optional[datetime]
    geo: Optional[LatLon]

    @property
    def _basename(self) -> str:
        # TODO 'canonical' or something? only makes sense for organized ones
        for bp in config.paths:
            if self.path.startswith(bp):
                return self.path[len(bp):]
        raise RuntimeError(f"Weird path {self.path}, can't match against anything")

    @property
    def name(self) -> str:
        return self._basename.strip('/')

    @property
    def url(self) -> str:
        # TODO belongs to private overlay..
        return f'{config.base_url}{self._basename}'


from .utils import Exif, ExifTags, convert_ref, dt_from_path, get_exif_from_file

Result = Res[Photo]

def _make_photo_aux(*args, **kwargs) -> list[Result]:
    # for the process pool..
    return list(_make_photo(*args, **kwargs))

def _make_photo(photo: Path, mtype: str, *, parent_geo: LatLon | None) -> Iterator[Result]:
    exif: Exif
    if any(x in mtype for x in ['image/png', 'image/x-ms-bmp', 'video']):
        # TODO don't remember why..
        logger.debug(f"skipping exif extraction for {photo} due to mime {mtype}")
        exif = {}
    else:
        try:
            exif = get_exif_from_file(photo)
        except Exception as e:
            # TODO add exception note?
            yield e
            exif = {}

    def _get_geo() -> LatLon | None:
        meta = exif.get(ExifTags.GPSINFO, {})
        if ExifTags.LAT in meta and ExifTags.LON in meta:
            return LatLon(
                lat=convert_ref(meta[ExifTags.LAT], meta[ExifTags.LAT_REF]),
                lon=convert_ref(meta[ExifTags.LON], meta[ExifTags.LON_REF]),
            )
        return parent_geo

    # TODO aware on unaware?
    def _get_dt() -> datetime | None:
        edt = exif.get(ExifTags.DATETIME, None)
        if edt is not None:
            dtimes = edt.replace(' 24', ' 00')  # jeez maybe log it?
            if dtimes == "0000:00:00 00:00:00":
                logger.warning(f"Bad exif timestamp {dtimes} for {photo}")
            else:
                dt = datetime.strptime(dtimes, '%Y:%m:%d %H:%M:%S')
                # TODO timezone is local, should take into account...
                return dt

        if 'Instagram/VID_' in str(photo):
            # TODO bit random...
            logger.warning('ignoring timestamp extraction for %s, they are stupid for Instagram videos', photo)
            return None

        edt = dt_from_path(photo)  # ok, last try..

        if edt is None:
            return None

        if edt > datetime.now():
            # TODO also yield?
            logger.error('datetime for %s is too far in future: %s', photo, edt)
            return None

        return edt

    geo = _get_geo()
    dt  = _get_dt()

    yield Photo(str(photo), dt=dt, geo=geo)


def _candidates() -> Iterable[Res[str]]:
    # TODO that could be a bit slow if there are to many extra files?
    from subprocess import PIPE, Popen
    # TODO could extract this to common?
    # TODO would be nice to reuse get_files  (or even let it use find)
    # that way would be easier to exclude
    with Popen([
            'fdfind',
            '--follow',
            '-t', 'file',
            '.',
            *config.paths,
    ], stdout=PIPE) as p:
        out = p.stdout; assert out is not None
        for line in out:
            path = line.decode('utf8').rstrip('\n')
            mime = fastermime(path)
            tp = mime.split('/')[0]
            if tp in {'inode', 'text', 'application', 'audio'}:
                continue
            if tp not in {'image', 'video'}:
                msg = f'{path}: unexpected mime {tp}'
                logger.warning(msg)
                yield RuntimeError(msg) # not sure if necessary
            # TODO return mime too? so we don't have to call it again in _photos?
            yield path


def photos() -> Iterator[Result]:
    candidates = tuple(sort_res_by(_candidates(), key=lambda i: i))
    return _photos(candidates)


# if geo information is missing from photo, you can specify it manually in geo.json file
# TODO is there something more standard?
@mcachew(cache_path=cache_dir())
def _photos(candidates: Iterable[Res[str]]) -> Iterator[Result]:
    geolocator = Nominatim() # TODO does it cache??

    from functools import lru_cache
    @lru_cache(None)
    def get_geo(d: Path) -> LatLon | None:
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

    pool = Pool()
    futures = []

    for p in candidates:
        if isinstance(p, Exception):
            yield p
            continue
        path = Path(p)
        # TODO rely on get_files
        if config.ignored(path):
            logger.info('ignoring %s due to config', path)
            continue

        logger.debug('processing %s', path)
        parent_geo = get_geo(path.parent)
        mime = fastermime(str(path))

        futures.append(pool.submit(_make_photo_aux, path, mime, parent_geo=parent_geo))

    for f in futures:
        yield from f.result()


def print_all() -> None:
    for p in photos():
        if isinstance(p, Exception):
            print('ERROR!', p)
        else:
            print(f"{p.dt!s:25} {p.path} {p.geo}")

# todo cachew -- improve AttributeError: type object 'tuple' has no attribute '__annotations__' -- improve errors?
# todo cachew -- invalidate if function code changed?

from ..core import Stats, stat


def stats() -> Stats:
    return stat(photos)
