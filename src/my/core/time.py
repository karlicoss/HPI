from __future__ import annotations

from collections.abc import Sequence
from functools import cache, lru_cache

import pytz

from .types import datetime_aware, datetime_naive


def user_forced() -> Sequence[str]:
    # conversion from abbreviations is always ambiguous
    # https://stackoverflow.com/questions/36067621/python-all-possible-timezone-abbreviations-for-given-timezone-name-and-vise-ve
    try:
        from my.config import time as user_config

        return user_config.tz.force_abbreviations  # type: ignore[attr-defined]  # noqa: TRY300
        # note: noqa since we're catching case where config doesn't have attribute here as well
    except:
        # todo log/apply policy
        return []


@lru_cache(1)
def _abbr_to_timezone_map() -> dict[str, pytz.BaseTzInfo]:
    # also force UTC to always correspond to utc
    # this makes more sense than Zulu it ends up by default
    timezones = [*pytz.all_timezones, 'UTC', *user_forced()]

    res: dict[str, pytz.BaseTzInfo] = {}
    for tzname in timezones:
        tz = pytz.timezone(tzname)
        infos = getattr(tz, '_tzinfos', [])  # not sure if can rely on attr always present?
        for info in infos:
            abbr = info[-1]
            # todo could support this with a better error handling strategy?
            # otz = res.get(abbr, tz)
            # if otz != tz:
            #     raise RuntimeError(abbr, tz, otz)
            res[abbr] = tz
        # ugh. also necessary, e.g. for Zulu?? why is it not in _tzinfos?
        # note: somehow this is not the same as the tzname!
        tzn = getattr(tz, '_tzname', None)
        if tzn is not None:
            res[tzn] = tz
    return res


@cache
def abbr_to_timezone(abbr: str) -> pytz.BaseTzInfo:
    return _abbr_to_timezone_map()[abbr]


def localize_with_abbr(dt: datetime_naive, *, abbr: str) -> datetime_aware:
    if abbr.lower() == 'utc':
        # best to shortcut here to avoid complications
        return pytz.utc.localize(dt)

    tz = abbr_to_timezone(abbr)
    # this will compute the correct UTC offset
    tzinfo = tz.localize(dt).tzinfo
    assert tzinfo is not None  # make mypy happy
    return tz.normalize(dt.replace(tzinfo=tzinfo))


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


# todo stuff here could be a bit more defensive? e.g. dependent on policy
