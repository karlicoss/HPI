from datetime import datetime
from typing import Callable, cast

from ...core.common import tzdatetime, Literal


'''
Depending on the specific data provider and your level of paranoia you might expect different behaviour.. E.g.:
- if your objects already have tz info, you might not need to call localize() at all
- it's safer when either all of your objects are tz aware or all are tz unware, not a mixture
- you might trust your original timezone, or it might just be UTC, and you want to use something more reasonable
'''
Policy = Literal[
    'keep'   , # if datetime is tz aware, just preserve it
    'convert', # if datetime is tz aware, convert to provider's tz
    'throw'  , # if datetime is tz aware, throw exception
    # todo 'warn'? not sure if very useful
]

def default_policy() -> Policy:
    try:
        from my.config import time as user_config
        return cast(Policy, user_config.tz.policy)
    except Exception as e:
        # todo meh.. need to think how to do this more carefully
        # rationale: do not mess with user's data unless they want
        return 'keep'


def localize_with_policy(lfun: Callable[[datetime], tzdatetime], dt: datetime, policy: Policy=default_policy()) -> tzdatetime:
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
