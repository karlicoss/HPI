from pathlib import Path
from typing import Dict

import PIL.Image # type: ignore
from PIL.ExifTags import TAGS, GPSTAGS # type: ignore


Exif = Dict

# TODO PIL.ExifTags.TAGS


class ExifTags:
    DATETIME = "DateTimeOriginal"
    LAT      = "GPSLatitude"
    LAT_REF  = "GPSLatitudeRef"
    LON      = "GPSLongitude"
    LON_REF  = "GPSLongitudeRef"
    GPSINFO  = "GPSInfo"


# TODO there must be something more standard for this...
def get_exif_from_file(path: Path) -> Exif:
    # TODO exception handler?
    with PIL.Image.open(str(path)) as fo:
        return get_exif_data(fo)


def get_exif_data(image):
    """Returns a dictionary from the exif data of an PIL Image item. Also converts the GPS Tags"""
    exif_data = {}
    info = image._getexif()
    if info:
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == ExifTags.GPSINFO:
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


def convert_ref(cstr, ref: str):
    val = to_degree(cstr)
    if ref == 'S' or ref == 'W':
        val = -val
    return val



import re
from datetime import datetime
from typing import Optional

# TODO surely there is a library that does it??
_DT_REGEX = re.compile(r'\D(\d{8})\D*(\d{6})\D')
def dt_from_path(p: Path) -> Optional[datetime]:
    name = p.stem
    mm = _DT_REGEX.search(name)
    if mm is None:
        return None
    dates = mm.group(1) + mm.group(2)
    return datetime.strptime(dates, "%Y%m%d%H%M%S")

from ..core import __NOT_HPI_MODULE__
