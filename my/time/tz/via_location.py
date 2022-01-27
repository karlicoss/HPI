'''
Timezone data provider, guesses timezone based on location data (e.g. GPS)
'''
REQUIRES = [
    # for determining timezone by coordinate
    'timezonefinder',
]


from collections import Counter
from datetime import date, datetime
from functools import lru_cache
from itertools import groupby
from typing import Iterator, NamedTuple, Optional

from more_itertools import seekable
import pytz

from ...core.common import LazyLogger, mcachew, tzdatetime
from ...core.cachew import cache_dir
from ...location.google import locations


logger = LazyLogger(__name__, level='debug')


# todo should move to config? not sure
_FASTER: bool = True
@lru_cache(2)
def _timezone_finder(fast: bool):
    if fast:
        # less precise, but faster
        from timezonefinder import TimezoneFinderL as Finder  # type: ignore
    else:
        from timezonefinder import TimezoneFinder  as Finder # type: ignore
    return Finder(in_memory=True)


# todo move to common?
Zone = str


# NOTE: for now only daily resolution is supported... later will implement something more efficient
class DayWithZone(NamedTuple):
    day: date
    zone: Zone


def _iter_local_dates(start=0, stop=None) -> Iterator[DayWithZone]:
    finder = _timezone_finder(fast=_FASTER) # rely on the default
    pdt = None
    warnings = []
    # todo allow to skip if not noo many errors in row?
    for l in locations(start=start, stop=stop):
        # TODO right. its _very_ slow...
        zone = finder.timezone_at(lng=l.lon, lat=l.lat)
        if zone is None:
            warnings.append(f"Couldn't figure out tz for {l}")
            continue
        tz = pytz.timezone(zone)
        # TODO this is probably a bit expensive... test & benchmark
        ldt = l.dt.astimezone(tz)
        ndate = ldt.date()
        if pdt is not None and ndate < pdt.date():
            # TODO for now just drop and collect the stats
            # I guess we'd have minor drops while air travel...
            warnings.append("local time goes backwards {ldt} ({tz}) < {pdt}")
            continue
        pdt = ldt
        z = tz.zone; assert z is not None
        yield DayWithZone(day=ndate, zone=z)


def most_common(l):
    res, count = Counter(l).most_common(1)[0] # type: ignore[var-annotated]
    return res


@mcachew(cache_path=cache_dir())
def _iter_tzs() -> Iterator[DayWithZone]:
    for d, gr in groupby(_iter_local_dates(), key=lambda p: p.day):
        logger.info('processed %s', d)
        zone = most_common(list(gr)).zone
        yield DayWithZone(day=d, zone=zone)


@lru_cache(1)
def loc_tz_getter() -> Iterator[DayWithZone]:
    # seekable makes it cache the emitted values
    return seekable(_iter_tzs())


# todo expose zone names too?
@lru_cache(maxsize=None)
def _get_day_tz(d: date) -> Optional[pytz.BaseTzInfo]:
    sit = loc_tz_getter()
    # todo hmm. seeking is not super efficient... might need to use some smarter dict-based cache
    # hopefully, this method itself caches stuff forthe users, so won't be too bad
    sit.seek(0) # type: ignore

    zone: Optional[str] = None
    for x, tz in sit:
        if x == d:
            zone = tz
        if x >= d:
            break
    return None if zone is None else pytz.timezone(zone)

# ok to cache, there are only a few home locations?
@lru_cache(maxsize=None)
def _get_home_tz(loc) -> Optional[pytz.BaseTzInfo]:
    (lat, lng) = loc
    finder = _timezone_finder(fast=False) # ok to use slow here for better precision
    zone = finder.timezone_at(lat=lat, lng=lng)
    if zone is None:
        # TODO shouldn't really happen, warn?
        return None
    else:
        return pytz.timezone(zone)


# TODO expose? to main as well?
def _get_tz(dt: datetime) -> Optional[pytz.BaseTzInfo]:
    res = _get_day_tz(d=dt.date())
    if res is not None:
        return res
    # fallback to home tz
    from ...location import home
    loc = home.get_location(dt)
    return _get_home_tz(loc=loc)


def localize(dt: datetime) -> tzdatetime:
    tz = _get_tz(dt)
    if tz is None:
        # TODO -- this shouldn't really happen.. think about it carefully later
        return dt
    else:
        return tz.localize(dt)


from ...core import stat, Stats
def stats() -> Stats:
    # TODO not sure what would be a good stat() for this module...
    # might be nice to print some actual timezones?
    # there aren't really any great iterables to expose
    def localized_years():
        last = datetime.now().year + 2
        # note: deliberately take + 2 years, so the iterator exhausts. otherwise stuff might never get cached
        # need to think about it...
        for Y in range(1990, last):
            dt = datetime.fromisoformat(f'{Y}-01-01 01:01:01')
            yield localize(dt)
    return stat(localized_years)
