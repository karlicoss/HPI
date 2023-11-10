'''
Timezone data provider, guesses timezone based on location data (e.g. GPS)
'''
REQUIRES = [
    # for determining timezone by coordinate
    'timezonefinder',
]

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
import heapq
from itertools import groupby
import os
from typing import Iterator, Optional, Tuple, Any, List, Iterable, Set, Dict

import pytz

from my.core import make_logger, stat, Stats, datetime_aware
from my.core.common import mcachew
from my.core.source import import_source
from my.core.warnings import high

from my.location.common import LatLon


## user might not have tz config section, so makes sense to be more defensive about it
# todo might be useful to extract a helper for this
try:
    from my.config import time
except ImportError as ie:
    if ie.name != 'time':
        raise ie
else:
    try:
        user_config = time.tz.via_location
    except AttributeError as ae:
        if not ("'tz'" in str(ae) or "'via_location'"):
            raise ae

# deliberately dynamic to prevent confusing mypy
if 'user_config' not in globals():
    globals()['user_config'] = object
##


@dataclass
class config(user_config):
    # less precise, but faster
    fast: bool = True

    # sort locations by date
    # in case multiple sources provide them out of order
    sort_locations: bool = True

    # if the accuracy for the location is more than 5km, don't use
    require_accuracy: float = 5_000

    # how often (hours) to refresh the cachew timezone cache
    # this may be removed in the future if we opt for dict-based caching
    _iter_tz_refresh_time: int = 6


logger = make_logger(__name__)


@lru_cache(None)
def _timezone_finder(fast: bool) -> Any:
    if fast:
        # less precise, but faster
        from timezonefinder import TimezoneFinderL as Finder
    else:
        from timezonefinder import TimezoneFinder as Finder  # type: ignore
    return Finder(in_memory=True)


# for backwards compatibility
def _locations() -> Iterator[Tuple[LatLon, datetime_aware]]:
    try:
        import my.location.all

        for loc in my.location.all.locations():
            if loc.accuracy is not None and loc.accuracy > config.require_accuracy:
                continue
            yield ((loc.lat, loc.lon), loc.dt)

    except Exception as e:
        logger.exception(
            "Could not setup via_location using my.location.all provider, falling back to legacy google implementation", exc_info=e
        )
        high("Setup my.google.takeout.parser, then my.location.all for better google takeout/location data")

        import my.location.google

        for gloc in my.location.google.locations():
            yield ((gloc.lat, gloc.lon), gloc.dt)


# TODO: could use heapmerge or sort the underlying iterators somehow?
# see https://github.com/karlicoss/HPI/pull/237#discussion_r858372934
def _sorted_locations() -> List[Tuple[LatLon, datetime_aware]]:
    return sorted(_locations(), key=lambda x: x[1])


# todo move to common?
Zone = str


# NOTE: for now only daily resolution is supported... later will implement something more efficient
@dataclass(unsafe_hash=True)
class DayWithZone:
    day: date
    zone: Zone


def _find_tz_for_locs(finder: Any, locs: Iterable[Tuple[LatLon, datetime]]) -> Iterator[DayWithZone]:
    for (lat, lon), dt in locs:
        # TODO right. its _very_ slow...
        zone = finder.timezone_at(lat=lat, lng=lon)
        # todo allow to skip if not noo many errors in row?
        if zone is None:
            # warnings.append(f"Couldn't figure out tz for {lat}, {lon}")
            continue
        tz = pytz.timezone(zone)
        # TODO this is probably a bit expensive... test & benchmark
        ldt = dt.astimezone(tz)
        ndate = ldt.date()
        # if pdt is not None and ndate < pdt.date():
        #    # TODO for now just drop and collect the stats
        #    # I guess we'd have minor drops while air travel...
        #    warnings.append("local time goes backwards {ldt} ({tz}) < {pdt}")
        #    continue
        # pdt = ldt
        z = tz.zone
        assert z is not None
        yield DayWithZone(day=ndate, zone=z)


# Note: this takes a while, as the upstream since _locations isn't sorted, so this
# has to do an iterative sort of the entire my.locations.all list
def _iter_local_dates() -> Iterator[DayWithZone]:
    finder = _timezone_finder(fast=config.fast)  # rely on the default
    # pdt = None
    # TODO: warnings doesn't actually warn?
    # warnings = []

    locs: Iterable[Tuple[LatLon, datetime]]
    locs = _sorted_locations() if config.sort_locations else _locations()

    yield from _find_tz_for_locs(finder, locs)


# my.location.fallback.estimate_location could be used here
# but iterating through all the locations is faster since this
# is saved behind cachew
@import_source(module_name="my.location.fallback.all")
def _iter_local_dates_fallback() -> Iterator[DayWithZone]:
    from my.location.fallback.all import fallback_locations as flocs

    def _fallback_locations() -> Iterator[Tuple[LatLon, datetime]]:
        for loc in sorted(flocs(), key=lambda x: x.dt):
            yield ((loc.lat, loc.lon), loc.dt)

    yield from _find_tz_for_locs(_timezone_finder(fast=config.fast), _fallback_locations())


def most_common(lst: Iterator[DayWithZone]) -> DayWithZone:
    res, _ = Counter(lst).most_common(1)[0]
    return res


def _iter_tz_depends_on() -> str:
    """
    Since you might get new data which specifies a new timezone sometime
    in the day, this causes _iter_tzs to refresh every _iter_tz_refresh_time hours
    (default 6), like:
    2022-04-26_00
    2022-04-26_06
    2022-04-26_12
    2022-04-26_18
    """
    mod = config._iter_tz_refresh_time
    assert mod >= 1
    day = str(date.today())
    hr = datetime.now().hour
    hr_truncated = hr // mod * mod
    return "{}_{}".format(day, hr_truncated)


# refresh _iter_tzs every few hours -- don't think a better depends_on is possible dynamically
@mcachew(depends_on=_iter_tz_depends_on)
def _iter_tzs() -> Iterator[DayWithZone]:
    # since we have no control over what order the locations are returned,
    # we need to sort them first before we can do a groupby
    by_day = lambda p: p.day

    local_dates: List[DayWithZone] = sorted(_iter_local_dates(), key=by_day)
    logger.debug(f"no. of items using exact locations: {len(local_dates)}")

    local_dates_fallback: List[DayWithZone] = sorted(_iter_local_dates_fallback(), key=by_day)

    # find days that are in fallback but not in local_dates (i.e., missing days)
    local_dates_set: Set[date] = {d.day for d in local_dates}
    use_fallback_days: List[DayWithZone] = [d for d in local_dates_fallback if d.day not in local_dates_set]
    logger.debug(f"no. of items being used from fallback locations: {len(use_fallback_days)}")

    # combine local_dates and missing days from fallback into a sorted list
    all_dates = heapq.merge(local_dates, use_fallback_days, key=by_day)
    # todo could probably use heapify here instead of heapq.merge?

    for d, gr in groupby(all_dates, key=by_day):
        logger.debug(f"processed {d}{', using fallback' if d in local_dates_set else ''}")
        zone = most_common(gr).zone
        yield DayWithZone(day=d, zone=zone)


@lru_cache(1)
def _day2zone() -> Dict[date, pytz.BaseTzInfo]:
    # NOTE: kinda unfortunate that this will have to process all days before returning result for just one
    # however otherwise cachew cache might never be initialized properly
    # so we'll always end up recomputing everyting during subsequent runs
    return {dz.day: pytz.timezone(dz.zone) for dz in _iter_tzs()}


def _get_day_tz(d: date) -> Optional[pytz.BaseTzInfo]:
    return _day2zone().get(d)


# ok to cache, there are only a few home locations?
@lru_cache(None)
def _get_home_tz(loc: LatLon) -> Optional[pytz.BaseTzInfo]:
    (lat, lng) = loc
    finder = _timezone_finder(fast=False)  # ok to use slow here for better precision
    zone = finder.timezone_at(lat=lat, lng=lng)
    if zone is None:
        # TODO shouldn't really happen, warn?
        return None
    else:
        return pytz.timezone(zone)


def get_tz(dt: datetime) -> Optional[pytz.BaseTzInfo]:
    '''
    Given a datetime, returns the timezone for that date.
    '''
    res = _get_day_tz(d=dt.date())
    if res is not None:
        return res
    # fallback to home tz
    # note: the fallback to fallback.via_home.estimate_location is still needed, since
    # _iter_local_dates_fallback only returns days which we actually have a datetime for
    # (e.g. there was an IP address within a day of that datetime)
    #
    # given a datetime, fallback.via_home.estimate_location will find which home location
    # that datetime is between, else fallback on your first home location, so it acts
    # as a last resort
    from my.location.fallback import via_home as home

    loc = list(home.estimate_location(dt))
    assert len(loc) == 1, f"should only have one home location, received {loc}"
    return _get_home_tz(loc=(loc[0].lat, loc[0].lon))


def localize(dt: datetime) -> datetime_aware:
    tz = get_tz(dt)
    if tz is None:
        # TODO -- this shouldn't really happen.. think about it carefully later
        return dt
    else:
        return tz.localize(dt)


def stats(quick: bool = False) -> Stats:
    if quick:
        prev, config.sort_locations = config.sort_locations, False
        res = {'first': next(_iter_local_dates())}
        config.sort_locations = prev
        return res
    # TODO not sure what would be a good stat() for this module...
    # might be nice to print some actual timezones?
    # there aren't really any great iterables to expose
    VIA_LOCATION_START_YEAR = int(os.environ.get("VIA_LOCATION_START_YEAR", 1990))

    def localized_years():
        last = datetime.now().year + 2
        # note: deliberately take + 2 years, so the iterator exhausts. otherwise stuff might never get cached
        # need to think about it...
        for Y in range(VIA_LOCATION_START_YEAR, last):
            dt = datetime.fromisoformat(f'{Y}-01-01 01:01:01')
            yield localize(dt)

    return stat(localized_years)


# deprecated -- still used in some other modules so need to keep
_get_tz = get_tz
