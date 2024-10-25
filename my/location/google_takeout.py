"""
Extracts locations using google_takeout_parser -- no shared code with the deprecated my.location.google
"""

REQUIRES = ["git+https://github.com/purarue/google_takeout_parser"]

from collections.abc import Iterator

from google_takeout_parser.models import Location as GoogleLocation

from my.core import LazyLogger, Stats, stat
from my.core.cachew import mcachew
from my.google.takeout.parser import _cachew_depends_on, events

from .common import Location

logger = LazyLogger(__name__)


@mcachew(
    depends_on=_cachew_depends_on,
    logger=logger,
)
def locations() -> Iterator[Location]:
    for g in events():
        if isinstance(g, GoogleLocation):
            yield Location(
                lon=g.lng,
                lat=g.lat,
                dt=g.dt,
                accuracy=g.accuracy,
                elevation=None,
                datasource="google_takeout",
            )


def stats() -> Stats:
    return stat(locations)
