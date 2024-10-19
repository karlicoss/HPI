"""
Parse [[https://github.com/mendhak/gpslogger][gpslogger]] .gpx (xml) files
"""

REQUIRES = ["gpxpy"]


from dataclasses import dataclass

from my.config import location
from my.core import Paths


@dataclass
class config(location.gpslogger):
    # path[s]/glob to the synced gpx (XML) files
    export_path: Paths

    # default accuracy for gpslogger
    accuracy: float = 50.0


from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from itertools import chain
from pathlib import Path

import gpxpy
from gpxpy.gpx import GPXXMLSyntaxException
from more_itertools import unique_everseen

from my.core import LazyLogger, Stats
from my.core.cachew import mcachew
from my.core.common import get_files

from .common import Location

logger = LazyLogger(__name__, level="warning")

def _input_sort_key(path: Path) -> str:
    if "_" in path.name:
        return path.name.split("_", maxsplit=1)[1]
    return path.name


def inputs() -> Sequence[Path]:
    # gpslogger files can optionally be prefixed by a device id,
    # like b5760c66102a5269_20211214142156.gpx
    return sorted(get_files(config.export_path, glob="*.gpx", sort=False), key=_input_sort_key)


def _cachew_depends_on() -> list[float]:
    return [p.stat().st_mtime for p in inputs()]


# TODO: could use a better cachew key/this has to recompute every file whenever the newest one changes
@mcachew(depends_on=_cachew_depends_on, logger=logger)
def locations() -> Iterator[Location]:
    yield from unique_everseen(
        chain(*map(_extract_locations, inputs())), key=lambda loc: loc.dt
    )


def _extract_locations(path: Path) -> Iterator[Location]:
    with path.open("r") as gf:
        try:
            gpx_obj = gpxpy.parse(gf)
        except GPXXMLSyntaxException as e:
            logger.warning("failed to parse XML %s: %s", path, e)
            return
        for track in gpx_obj.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.time is None:
                        continue
                    # hmm - for gpslogger, seems that timezone is always SimpleTZ('Z'), which
                    # specifies UTC -- see https://github.com/tkrajina/gpxpy/blob/cb243b22841bd2ce9e603fe3a96672fc75edecf2/gpxpy/gpxfield.py#L38
                    yield Location(
                        lat=point.latitude,
                        lon=point.longitude,
                        accuracy=config.accuracy,
                        elevation=point.elevation,
                        dt=datetime.replace(point.time, tzinfo=timezone.utc),
                        datasource="gpslogger",
                    )


def stats() -> Stats:
    from my.core import stat

    return {**stat(locations)}
