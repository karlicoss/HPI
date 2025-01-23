from __future__ import annotations

from ..core import __NOT_HPI_MODULE__  # isort: skip

from pathlib import Path

import PIL.Image
from PIL.ExifTags import GPSTAGS, TAGS

Exif = dict

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
        return _get_exif_data(fo)


def _get_exif_data(image) -> Exif:
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


def to_degree(value) -> float:
    """Helper function to convert the GPS coordinates
    stored in the EXIF to digress in float format"""
    (d, m, s) = value
    return d + (m / 60.0) + (s / 3600.0)


def convert_ref(cstr, ref: str) -> float:
    val = to_degree(cstr)
    if ref == 'S' or ref == 'W':
        val = -val
    return val


import re
from datetime import datetime

# TODO surely there is a library that does it??
# TODO this belongs to a private overlay or something
# basically have a function that patches up dates after the files were yielded..
_DT_REGEX = re.compile(r'\D(\d{8})\D*(\d{6})\D')
def dt_from_path(p: Path) -> datetime | None:
    name = p.stem
    mm = _DT_REGEX.search(name)
    if mm is None:
        return None
    dates = mm.group(1) + mm.group(2)
    return datetime.strptime(dates, "%Y%m%d%H%M%S")
