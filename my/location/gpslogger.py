"""
Parse [[https://github.com/mendhak/gpslogger][gpslogger]] .gpx (xml) files
"""

REQUIRES = ["gpxpy"]

from my.config import location
from my.core import Paths, dataclass


@dataclass
class config(location.gpslogger):
    # path[s]/glob to the synced gpx (XML) files
    export_path: Paths

    # default accuracy for gpslogger
    accuracy: float = 50.0


from itertools import chain
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence, List

import gpxpy  # type: ignore[import]
from more_itertools import unique_everseen

from my.core import Stats, LazyLogger
from my.core.common import get_files, mcachew
from .common import Location


logger = LazyLogger(__name__, level="warning")


def inputs() -> Sequence[Path]:
    return get_files(config.export_path, glob="*.gpx")


def _cachew_depends_on() -> List[float]:
    return [p.stat().st_mtime for p in inputs()]


# TODO: could use a better cachew key/this has to recompute every file whenever the newest one changes
@mcachew(depends_on=_cachew_depends_on, logger=logger)
def locations() -> Iterator[Location]:
    yield from unique_everseen(
        chain(*map(_extract_locations, inputs())), key=lambda loc: loc.dt
    )


def _extract_locations(path: Path) -> Iterator[Location]:
    with path.open("r") as gf:
        gpx_obj = gpxpy.parse(gf)
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
                    )


def stats() -> Stats:
    from my.core import stat

    return {**stat(locations)}
