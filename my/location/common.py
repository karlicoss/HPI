from my.core import __NOT_HPI_MODULE__  # isort: skip

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Protocol, TextIO, Union

DateIsh = Union[datetime, date, str]

LatLon = tuple[float, float]


class LocationProtocol(Protocol):
    lat: float
    lon: float
    dt: datetime
    accuracy: Optional[float]
    elevation: Optional[float]
    datasource: Optional[str] = None  # which module provided this, useful for debugging


# TODO: add timezone to this? can use timezonefinder in tz provider instead though


# converted from namedtuple to a dataclass so datasource field can be added optionally
# if we want, can eventually be converted back to a namedtuple when all datasources are compliant
@dataclass(frozen=True, eq=True)
class Location(LocationProtocol):
    lat: float
    lon: float
    dt: datetime
    accuracy: Optional[float]
    elevation: Optional[float]
    datasource: Optional[str] = None  # which module provided this, useful for debugging


def locations_to_gpx(locations: Iterable[LocationProtocol], buffer: TextIO) -> Iterator[Exception]:
    """
    Convert locations to a GPX file, printing to a buffer (an open file, io.StringIO, sys.stdout, etc)
    """

    try:
        import gpxpy.gpx
    except ImportError as ie:
        from my.core.warnings import high

        high("gpxpy not installed, cannot write to gpx. 'pip install gpxpy'")
        raise ie

    gpx = gpxpy.gpx.GPX()

    # hmm -- would it be useful to allow the user to split this into tracks?, perhaps by date?

    # Create first track in our GPX:
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)

    # Create first segment in our GPX track:
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)


    for location in locations:
        try:
            point = gpxpy.gpx.GPXTrackPoint(
                latitude=location.lat,
                longitude=location.lon,
                elevation=location.elevation,
                time=location.dt,
                comment=location.datasource,
            )
        except AttributeError:
            yield TypeError(
                f"Expected a Location or Location-like object, got {type(location)} {location!r}"
            )
            continue
        gpx_segment.points.append(point)

    buffer.write(gpx.to_xml())
