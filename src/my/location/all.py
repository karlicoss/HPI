"""
Merges location data from multiple sources
"""

from collections.abc import Iterator

from my.core import LazyLogger, Stats
from my.core.source import import_source

from .common import Location

logger = LazyLogger(__name__, level="warning")


def locations() -> Iterator[Location]:
    # can add/comment out sources here to disable them, or use core.disabled_modules
    yield from _takeout_locations()
    yield from _takeout_semantic_locations()
    yield from _gpslogger_locations()
    yield from _ip_locations()


@import_source(module_name="my.location.google_takeout")
def _takeout_locations() -> Iterator[Location]:
    from . import google_takeout
    yield from google_takeout.locations()


@import_source(module_name="my.location.google_takeout_semantic")
def _takeout_semantic_locations() -> Iterator[Location]:
    from . import google_takeout_semantic

    for event in google_takeout_semantic.locations():
        if isinstance(event, Exception):
            logger.error(f"google_takeout_semantic: {event}")
            continue
        yield event


@import_source(module_name="my.location.gpslogger")
def _gpslogger_locations() -> Iterator[Location]:
    from . import gpslogger
    yield from gpslogger.locations()


# TODO: remove, user should use fallback.estimate_location or fallback.fallback_locations instead
@import_source(module_name="my.location.via_ip")
def _ip_locations() -> Iterator[Location]:
    from . import via_ip
    yield from via_ip.locations()


def stats() -> Stats:
    from my.core import stat

    return {
        **stat(locations),
    }
