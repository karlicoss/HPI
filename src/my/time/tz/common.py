from datetime import datetime
from typing import Callable, Literal

from my.core import datetime_aware

'''
Depending on the specific data provider and your level of paranoia you might expect different behaviour.. E.g.:
- if your objects already have tz info, you might not need to call localize() at all
- it's safer when either all of your objects are tz aware or all are tz unware, not a mixture
- you might trust your original timezone, or it might just be UTC, and you want to use something more reasonable
'''
TzPolicy = Literal[
    'keep'   , # if datetime is tz aware, just preserve it
    'convert', # if datetime is tz aware, convert to provider's tz
    'throw'  , # if datetime is tz aware, throw exception
    # todo 'warn'? not sure if very useful
]

# backwards compatibility
Policy = TzPolicy

def default_policy() -> TzPolicy:
    try:
        from my.config import time as user_config
        res = user_config.tz.policy
    except Exception as _e:
        # todo meh.. need to think how to do this more carefully
        # rationale: do not mess with user's data unless they want
        return 'keep'
    else:
        return res


def localize_with_policy(
    lfun: Callable[[datetime], datetime_aware],
    dt: datetime,
    policy: TzPolicy=default_policy()  # noqa: B008
) -> datetime_aware:
    tz = dt.tzinfo
    if tz is None:
        return lfun(dt)

    if   policy == 'keep':
        return dt
    elif policy == 'convert':
        ldt = lfun(dt.replace(tzinfo=None))
        return dt.astimezone(ldt.tzinfo)
    else: # policy == 'error':
        raise RuntimeError(f"{dt} already has timezone information (use 'policy' argument to adjust this behaviour)")
