from functools import lru_cache
from datetime import datetime, tzinfo

import pytz # type: ignore

# https://gist.github.com/edwardabraham/8680198
tz_lookup = {
    pytz.timezone(x).localize(datetime.now()).tzname(): pytz.timezone(x)
    for x in pytz.all_timezones
}
tz_lookup['UTC'] = pytz.utc # ugh. otherwise it'z Zulu...


# TODO dammit, lru_cache interferes with mypy?
@lru_cache(None)
def abbr_to_timezone(abbr: str) -> tzinfo:
    return tz_lookup[abbr]


def zone_to_countrycode(zone: str) -> str:
    # todo make optional?
    return _zones_to_countrycode()[zone]


@lru_cache(1)
def _zones_to_countrycode():
    # https://stackoverflow.com/a/13020785/706389
    res = {}
    for countrycode, timezones in pytz.country_timezones.items():
        for timezone in timezones:
            res[timezone] = countrycode
    return res
