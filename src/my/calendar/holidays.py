"""
Holidays and days off work
"""
REQUIRES = [
    'workalendar', # library to determine public holidays
]

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Union

from my.core import Stats
from my.core.time import zone_to_countrycode


@lru_cache(1)
def _calendar():
    from workalendar.registry import registry

    # todo switch to using time.tz.main once _get_tz stabilizes?
    from ..time.tz import via_location as LTZ
    # TODO would be nice to do it dynamically depending on the past timezones...
    tz = LTZ.get_tz(datetime.now())
    assert tz is not None
    zone = tz.zone; assert zone is not None
    code = zone_to_countrycode(zone)
    Cal = registry.get_calendars()[code]
    return Cal()

# todo move to common?
DateIsh = Union[datetime, date, str]
def as_date(dd: DateIsh) -> date:
    if isinstance(dd, datetime):
        return dd.date()
    elif isinstance(dd, date):
        return dd
    else:
        # todo parse isoformat??
        return as_date(datetime.strptime(dd, '%Y%m%d'))


def is_holiday(d: DateIsh) -> bool:
    day = as_date(d)
    return not _calendar().is_working_day(day)


def is_workday(d: DateIsh) -> bool:
    return not is_holiday(d)


def stats() -> Stats:
    # meh, but not sure what would be a better test?
    res = {}
    year = datetime.now().year
    jan1 = date(year=year, month=1, day=1)
    for x in range(-7, 20):
        d = jan1 + timedelta(days=x)
        h = is_holiday(d)
        res[d.isoformat()] = 'holiday' if h else 'workday'
    return res
