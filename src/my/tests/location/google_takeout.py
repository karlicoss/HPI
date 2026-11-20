from datetime import UTC, datetime

from my.location.google_takeout import locations

from ..shared_tz_config import takeout_archive  # noqa: F401  # autoused fixture


def test_legacy_location_history() -> None:
    """Read the first and last GPS fixes from a 2017 Location History.json archive."""
    points = list(locations())
    first, last = points[0], points[-1]
    assert first.dt.replace(microsecond=0) == datetime(2017, 7, 29, 9, 59, 40, tzinfo=UTC)
    assert (first.lat, first.lon) == (46.6382052, 16.2043272)
    assert last.dt == datetime(2017, 8, 2, 13, 1, 56, tzinfo=UTC)
    assert (last.lat, last.lon) == (46.551535, 16.4742742)
