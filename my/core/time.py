from functools import lru_cache
from datetime import datetime

import pytz # type: ignore

# https://gist.github.com/edwardabraham/8680198
tz_lookup = {
    pytz.timezone(x).localize(datetime.now()).tzname(): pytz.timezone(x)
    for x in pytz.all_timezones
}
tz_lookup['UTC'] = pytz.utc # ugh. otherwise it'z Zulu...


@lru_cache(-1)
def abbr_to_timezone(abbr: str):
    return tz_lookup[abbr]
