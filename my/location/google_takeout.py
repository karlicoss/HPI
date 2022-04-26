"""
Extracts locations using google_takeout_parser -- no shared code with the deprecated my.location.google
"""

REQUIRES = ["git+https://github.com/seanbreckenridge/google_takeout_parser"]

from typing import Iterator

from my.google.takeout.parser import events, _cachew_depends_on
from google_takeout_parser.models import Location as GoogleLocation

from my.core.common import mcachew, LazyLogger, Stats
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
                lon=g.lng, lat=g.lat, dt=g.dt, accuracy=g.accuracy, elevation=None
            )


def stats() -> Stats:
    from my.core import stat

    return {**stat(locations)}
